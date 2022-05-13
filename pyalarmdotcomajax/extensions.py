"""Camera device classes."""
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
import asyncio
from enum import Enum
import logging
from typing import Any
from typing import TypedDict

import aiohttp
from bs4 import BeautifulSoup
from bs4 import Tag
from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.errors import UnexpectedDataStructure

from .helpers import extract_field_value

log = logging.getLogger(__name__)

# #################
# ### UNIVERSAL ###
# #################


class ExtendedProperties(TypedDict, total=False):
    """Extended properties to be made available in device core."""

    device_name: str
    config_id: str
    settings: dict[str, ConfigurationOption]  # Slug, ConfigurationOption
    raw_attribs: dict


class ConfigurationOptionType(Enum):
    """Specified types of configuration options."""

    CHIME = "chime"


class ConfigurationOption(TypedDict, total=False):
    """Dictionary of metadata for configuration options."""

    name: str
    slug: str
    current_value: Any
    option_type: ConfigurationOptionType
    value_type: type


class ControllerExtension(ABC):
    """Fetcher base class for device config data."""

    @abstractmethod
    async def fetch(
        self,
        websession: aiohttp.ClientSession,
        headers: dict,
        camera_names: list | None = None,
    ) -> list[ExtendedProperties]:
        """Retrieve updated configuration data for specified devices."""

        raise NotImplementedError

    @abstractmethod
    async def submit_change(
        self,
        camera_name: str,
        slug: str,
        updated_value: Any,
        websession: aiohttp.ClientSession,
        headers: dict,
    ) -> ExtendedProperties:
        """Change a setting."""

        raise NotImplementedError


# ###############
# ### SKYBELL ###
# ###############


class CameraSkybellControllerExtension(ControllerExtension):
    """Fetcher for Skybell HD config data."""

    ENDPOINT = f"{c.URL_BASE}/web/Video/SettingsMain_V2.aspx"

    # Fields not used for settings but required for form submission.
    _FORM_FIELDS_GENERIC = [
        "ctl00_ScriptManager1_HiddenField",
        "__EVENTTARGET",
        "__EVENTARGUMENT",
        "__LASTFOCUS",
        "__VIEWSTATE",
        "__VIEWSTATEGENERATOR",
        "__VIEWSTATEENCRYPTED",
        "__PREVIOUSPAGE",
        "__EVENTVALIDATION",
        "ctl00$key",
        "ctl00$phBody$hfRemoteAccessTestResult",
        "ctl00$phBody$hfAgeLimit",
        "ctl00$phBody$AutomaticClipDonationSettings$TextBoxClipQualityComments",
        "ctl00$phBody$ddlVideoQuality",
        "ctl00$phBody$ddChimeType",
        "ctl00$phBody$inpChimeLevel$bootstrapSlider",
        "ctl00$phBody$inpDoorbellLEDIntensity$bootstrapSlider",
        "ctl00$phBody$colorPicker",
        "ctl00$phBody$inpMotionThreshold$bootstrapSlider",
        "ctl00$phBody$bridgeInfo$tbCamName",
        "ctl00$phBody$bridgeInfo$tbBridgeLogin",
        "ctl00$phBody$bridgeInfo$tbBridgePwd",
        "ctl00$phBody$bridgeInfo$tbBridgePwdConfirm",
        "ctl00$phBody$bridgeInfo$hfSelectedDeviceId",
        "ctl00$phBody$bridgeInfo$wirelessSettings$ctl07",
        "ctl00$phBody$bridgeInfo$wirelessSettings$wirelessShowsBridge",
        "ctl00$phBody$bridgeInfo$wirelessSettings$txtSSID",
        "ctl00$phBody$bridgeInfo$wirelessSettings$ctl05",
        "ctl00$phBody$upgradeFirmwareMessageBox",
    ]

    # Fields containing camera metadata.
    _FORM_FIELDS_META = [
        ("ctl00$phBody$CamSelector$ddlCams", "config_id"),
        ("ctl00$phBody$tbCamName", "device_name"),
    ]

    # Fields containing configuration options.
    _FORM_FIELDS_SETTINGS: list[tuple[str, ConfigurationOption]] = [
        (
            "ctl00$phBody$cbIndoorChime",
            ConfigurationOption(
                {
                    "slug": "indoor_chime_on",
                    "name": "Indoor Chime",
                    "option_type": ConfigurationOptionType.CHIME,
                    "value_type": bool,
                }
            ),
        ),
        (
            "ctl00$phBody$cbOutdoorChime",
            ConfigurationOption(
                {
                    "slug": "outdoor_chime_on",
                    "name": "Outdoor Chime",
                    "option_type": ConfigurationOptionType.CHIME,
                    "value_type": bool,
                }
            ),
        ),
    ]

    async def fetch(
        self,
        websession: aiohttp.ClientSession,
        headers: dict,
        camera_names: list | None = None,
    ) -> list[ExtendedProperties]:
        """Retrieve updated configuration data for specified devices."""

        camera_return_data: list[ExtendedProperties] = []

        #
        # Initialize request variables and get data for first camera.
        #
        try:
            additional_camera_config_ids: list[str] = []

            async with websession.get(url=self.ENDPOINT, headers=headers) as resp:
                text = await resp.text()
                log.debug("Response status from Alarm.com: %s", resp.status)
                tree = BeautifulSoup(text, "html.parser")

                # Build list of cameras (everything or selection from camera_names)

                child: Tag
                for child in tree.select_one(
                    "#ctl00_phBody_CamSelector_ddlCams"
                ).findChildren():
                    camera_config_id: str = child.attrs.get("value")
                    if child.attrs.get("selected") == "selected":

                        # Retrieve data for camera on current page.
                        current_form_data = self._extract_fields(camera_config_id, tree)

                        if not camera_names or child.text in camera_names:
                            # Store data for current camera.
                            camera_return_data.append(current_form_data)
                    else:
                        # Add to camera config retrieval queue
                        additional_camera_config_ids.append(camera_config_id)

        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
            asyncio.exceptions.CancelledError,
        ) as err:
            log.error("Can not load settings page from Alarm.com")

            raise err
        except (AttributeError, IndexError) as err:
            log.error("Unable to extract page info from Alarm.com.")
            log.debug("Page contents:\n %s", text)
            raise UnexpectedDataStructure from err

        #
        # Get data for additional cameras.
        #
        try:
            for config_id in additional_camera_config_ids:
                # Build payload to request config page for next camera
                postback_form_data = current_form_data["raw_attribs"]
                postback_form_data["__EVENTTARGET"] = "ctl00$phBody$CamSelector$ddlCams"
                postback_form_data["ctl00$phBody$CamSelector$ddlCams"] = config_id

                async with websession.post(
                    url=self.ENDPOINT,
                    data=postback_form_data,
                    headers=headers,
                ) as resp:
                    text = await resp.text()
                    log.debug("Response status from Alarm.com: %s", resp.status)
                    tree = BeautifulSoup(text, "html.parser")

                    # Pull data for camera on current page
                    camera_return_data.append(
                        current_form_data := self._extract_fields(config_id, tree)
                    )
        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
            asyncio.exceptions.CancelledError,
        ) as err:
            log.error("Can not load settings page for additional camera from Alarm.com")

            raise err
        except UnexpectedDataStructure as err:
            log.debug("HTTP Response Status %s, Body:\n%s", resp.status, text)
            raise err

        return camera_return_data

    async def submit_change(
        self,
        camera_name: str,
        slug: str,
        updated_value: Any,
        websession: aiohttp.ClientSession,
        headers: dict,
    ) -> ExtendedProperties:
        """Change a setting."""

        #
        # Get field name for submitted value.
        #
        field_name: str | None = None

        try:

            for config_option_field_name, config_option in self._FORM_FIELDS_SETTINGS:
                if config_option["slug"] == slug:
                    field_name = config_option_field_name

        except KeyError as err:
            raise UnexpectedDataStructure("Slug not found.") from err

        #
        # Refresh settings data to prime submission payload.
        #
        results = await self.fetch(
            websession=websession, headers=headers, camera_names=[camera_name]
        )

        if not (payload := results[0].get("raw_attributes")) or not (
            config_id := results[0].get("config_id")
        ):
            raise UnexpectedDataStructure("Failed to refresh settings data for device.")

        #
        # Add updated value to payload.
        #
        try:
            if isinstance(payload, dict):
                payload[field_name] = updated_value
        except KeyError as err:
            raise UnexpectedDataStructure("Field name error.") from err

        #
        # Submit payload and refresh data.
        #
        try:
            async with websession.post(
                url=self.ENDPOINT, data=payload, headers=headers
            ) as resp:
                text = await resp.text()

                log.debug("Response status from Alarm.com: %s", resp.status)
                tree = BeautifulSoup(text, "html.parser")

                # Pull data for camera on current page
                camera_return_data = self._extract_fields(config_id, tree)

        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
            asyncio.exceptions.CancelledError,
        ) as err:
            log.error("Can not load settings page for additional camera from Alarm.com")

            raise err

        return camera_return_data

    async def _build_submit_payload(  # pylint: disable = no-self-use
        self, dynamic_form_data: dict
    ) -> dict:
        """Build POST body for submitting settings changes or for getting data for a different camera."""

        # Pre-populate static fields.
        form_data: dict = {
            "__SCROLLPOSITIONX": "0",
            "ctl00$phBody$CamSelector$ddlPage": "CameraInfo",
            "ctl00$phBody$AutomaticClipDonationSettings$ShowClipDonationLegalAgreement": (
                "1"
            ),
            "ctl00$phBody$tfSave": "Save",
            "ctl00$phBody$bridgeInfo$wirelessSettings$rblEncryption": "MakeASelection",
            "ctl00$phBody$bridgeInfo$wirelessSettings$rblAlgoritm": "MakeASelection",
            "ctl00$phBody$fwUpgradeModalTailTextBox": "Firmware+upgrade+is+complete.+You+can+check+the+video+device+status+after+closing+this+dialog+box.",
        }

        # Merge in dynamic fields with changesd values.
        form_data.update(dynamic_form_data)

        return form_data

    def _extract_fields(
        self, config_id: str, tree: BeautifulSoup
    ) -> ExtendedProperties:
        """Extract data from camera config page."""

        raw_attribs: dict = {}
        properties: ExtendedProperties = {
            "config_id": config_id,
            "settings": {},
        }

        try:
            for field_name in self._FORM_FIELDS_GENERIC:

                field = tree.find(attrs={"name": field_name})

                value = extract_field_value(field)

                raw_attribs[field_name] = value

            for field_name, property_name in self._FORM_FIELDS_META:

                field = tree.find(attrs={"name": field_name})

                value = extract_field_value(field)

                raw_attribs[field_name] = value
                properties[property_name] = value  # type: ignore

            for field_name, config_option in self._FORM_FIELDS_SETTINGS:

                field = tree.find(attrs={"name": field_name})

                value = extract_field_value(field)

                raw_attribs[field_name] = value
                config_option.update(ConfigurationOption({"current_value": value}))
                properties["settings"][config_option.get("slug")] = config_option  # type: ignore

        except UnexpectedDataStructure as err:
            log.error("Unable to extract field. Failed on field %s.", field_name)
            raise err

        properties["raw_attribs"] = raw_attribs

        return properties
