"""Configuration option extensions."""
from __future__ import annotations

from abc import ABC
from abc import abstractmethod
import asyncio
from dataclasses import dataclass
from enum import auto
from enum import Enum
import logging
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from bs4 import Tag
from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.errors import UnexpectedDataStructure

from .helpers import ExtendedEnumMixin
from .helpers import extract_field_value

log = logging.getLogger(__name__)

# #################
# ### UNIVERSAL ###
# #################


@dataclass
class ExtendedProperties:
    """Extended properties to be made available in device core."""

    config_id: str
    settings: dict[str, ConfigurationOption]  # Slug, ConfigurationOption
    device_name: str | None = None
    raw_attribs: dict | None = None


class ConfigurationOptionType(Enum):
    """Specified types of configuration options."""

    BINARY_CHIME = auto()
    ADJUSTABLE_CHIME = auto()
    BRIGHTNESS = auto()
    COLOR = auto()
    MOTION_SENSITIVITY = auto()


@dataclass
class ConfigurationOption:
    """Class for configuration options."""

    name: str
    slug: str
    option_type: ConfigurationOptionType
    value_type: type
    extension: type[CameraSkybellControllerExtension]
    user_configurable: bool

    current_value: Any | None = None
    value_min: int | None = None
    value_max: int | None = None
    value_regex: str | None = None
    show_as_hex: bool = False


class ControllerExtension(ABC):
    """Base class for extensions."""

    _description: str | None = None

    def __init__(self) -> None:
        """Initialize extension."""

    @property
    def description(self) -> str | None:
        """Describe extension purpose."""

        return self._description

    @abstractmethod
    async def fetch(
        self,
        camera_names: list | None = None,
    ) -> list[ExtendedProperties]:
        """Retrieve updated configuration data for specified devices."""

    @abstractmethod
    async def submit_change(
        self,
        camera_name: str,
        slug: str,
        new_value: Any,
    ) -> ConfigurationOption:
        """Change a setting."""


# ###############
# ### SKYBELL ###
# ###############


class CameraSkybellControllerExtension(ControllerExtension):
    """Fetcher for Skybell HD config data."""

    _description = "Adjust indoor and outdoor chimes for Skybell HD video doorbells."

    class ChimeAdjustableVolume(ExtendedEnumMixin):
        """Doorbell chime levels for bells with configurable volume."""

        OFF = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3

    class ChimeOnOff(ExtendedEnumMixin):
        """Doorbell chime levels for bells with configurable volume."""

        OFF = "off"
        ON = "on"

    class MotionSensitivity(ExtendedEnumMixin):
        """Camera motion sensor sensitivity."""

        LOW = 1
        MEDIUM = 2
        HIGH = 3
        VERY_HIGH = 4

    ENDPOINT = f"{c.URL_BASE}web/Video/SettingsMain_V2.aspx"

    _FORM_FIELD_OUTDOOR_CHIME_ONOFF = "ctl00$phBody$cbOutdoorChime"
    _FORM_FIELD_OUTDOOR_CHIME_VOLUME = "ctl00$phBody$inpChimeLevel$bootstrapSlider"
    _FORM_FIELD_INDOOR_CHIME_ONOFF = "ctl00$phBody$cbIndoorChime"
    _FORM_FIELD_LED_BRIGHTNESS = "ctl00$phBody$inpDoorbellLEDIntensity$bootstrapSlider"
    _FORM_FIELD_MOTION_SENSITIVITY = "ctl00$phBody$inpMotionThreshold$bootstrapSlider"
    _FORM_FIELD_LED_COLOR = "ctl00$phBody$colorPicker"

    _FORM_FIELDS_BYPASSABLE = [
        "__EVENTTARGET",
        "__EVENTARGUMENT",
        "__LASTFOCUS",
    ]

    # Fields not used for settings but required for form submission.
    _FORM_FIELDS_GENERIC = [
        "ctl00_ScriptManager1_HiddenField",
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

    def __init__(self, websession: aiohttp.ClientSession, headers: dict) -> None:
        """Initialize extension."""

        super().__init__()

        self._websession = websession
        self._headers = headers

        # Fields containing configuration options.
        self._form_field_settings: list[tuple[str, ConfigurationOption]] = [
            (
                self._FORM_FIELD_INDOOR_CHIME_ONOFF,
                ConfigurationOption(
                    slug="indoor-chime",
                    name="Indoor Chime",
                    option_type=ConfigurationOptionType.BINARY_CHIME,
                    value_type=self.ChimeOnOff,
                    extension=self.__class__,
                    user_configurable=True,
                ),
            ),
            (
                self._FORM_FIELD_OUTDOOR_CHIME_VOLUME,
                ConfigurationOption(
                    slug="outdoor-chime",
                    name="Outdoor Chime",
                    option_type=ConfigurationOptionType.ADJUSTABLE_CHIME,
                    value_type=self.ChimeAdjustableVolume,
                    extension=self.__class__,
                    user_configurable=True,
                ),
            ),
            (
                self._FORM_FIELD_OUTDOOR_CHIME_ONOFF,
                ConfigurationOption(
                    slug="outdoor-chime-onoff",
                    name="Outdoor Chime On/Off",
                    option_type=ConfigurationOptionType.BINARY_CHIME,
                    value_type=self.ChimeOnOff,
                    extension=self.__class__,
                    user_configurable=False,  # Outdoor chime on/off setting should be adjusted via volume setting ONLY.
                ),
            ),
            (
                self._FORM_FIELD_LED_BRIGHTNESS,
                ConfigurationOption(
                    slug="led-brightness",
                    name="LED Brightness",
                    option_type=ConfigurationOptionType.BRIGHTNESS,
                    value_type=int,
                    value_min=0,
                    value_max=100,
                    extension=self.__class__,
                    user_configurable=True,
                ),
            ),
            (
                self._FORM_FIELD_LED_COLOR,
                ConfigurationOption(
                    slug="led-color",
                    name="LED Color",
                    option_type=ConfigurationOptionType.COLOR,
                    value_type=str,
                    value_regex=r"(#[0-9a-fA-F]{6})",
                    extension=self.__class__,
                    user_configurable=True,
                ),
            ),
            (
                self._FORM_FIELD_MOTION_SENSITIVITY,
                ConfigurationOption(
                    slug="motion-sensitivity",
                    name="Motion Sensitivity",
                    option_type=ConfigurationOptionType.MOTION_SENSITIVITY,
                    value_type=self.MotionSensitivity,
                    extension=self.__class__,
                    user_configurable=True,
                ),
            ),
        ]

    async def fetch(
        self,
        camera_names: list | None = None,
    ) -> list[ExtendedProperties]:
        """Retrieve updated configuration data for specified devices."""

        camera_return_data: list[ExtendedProperties] = []

        #
        # Initialize request variables and get data for first camera.
        #
        try:
            additional_camera_config_ids: list[str] = []

            async with self._websession.get(
                url=self.ENDPOINT, headers=self._headers
            ) as resp:
                text = await resp.text()
                log.debug("Response status from Alarm.com: %s", resp.status)
                # log.debug("Response text from Alarm.com: %s", text)
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
            log.debug(
                "====== HTTP DUMP BEGIN ======\n%s\n====== HTTP DUMP END ======", text
            )
            raise UnexpectedDataStructure from err

        #
        # Get data for additional cameras.
        #
        try:
            for config_id in additional_camera_config_ids:
                # Build payload to request config page for next camera
                postback_form_data = current_form_data.raw_attribs

                if not postback_form_data:
                    raise UnexpectedDataStructure

                postback_form_data["__EVENTTARGET"] = "ctl00$phBody$CamSelector$ddlCams"
                postback_form_data["ctl00$phBody$CamSelector$ddlCams"] = config_id

                async with self._websession.post(
                    url=self.ENDPOINT,
                    data=postback_form_data,
                    headers=self._headers,
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
        new_value: Any,
    ) -> ConfigurationOption:
        """Change a setting."""

        # For non-volume adjustable chimes (indoor), value is "on" when checkbox is checked. Field is removed from POST payload when off.
        # For volume adjustable chimes (outdoor),  When on, either 1 for low, 2 for medium, 3 for high, or 0 for off.

        log.debug(
            "CameraSkybellControllerExtension -> submit_change(): Requested change for"
            " %s: %s to %s.",
            camera_name,
            slug,
            new_value,
        )

        #
        # Get field name for submitted value.
        #

        field_name: str
        field_value_type: type
        field_config_options: ConfigurationOption

        try:
            for config_option_field_name, config_option in self._form_field_settings:
                if config_option.slug == slug:
                    field_name = config_option_field_name
                    field_value_type = config_option.value_type
                    field_config_options = config_option

        except KeyError as err:
            raise UnexpectedDataStructure("Slug not found.") from err

        log.debug(
            "CameraSkybellControllerExtension -> submit_change(): Validating input."
        )

        #
        # VALIDATE INPUT
        #

        # Check that submitted value is correct type.
        # Currently only supports enums. In the future, should be expanded to also support native types.

        if field_value_type and not isinstance(new_value, field_value_type):
            raise TypeError(f"New value {new_value} is not of type {field_value_type}")

        # Validation for ints

        if field_value_type == int:
            if (
                (
                    (value_max := field_config_options.value_max)
                    and new_value > value_max
                )
                or (
                    (value_min := field_config_options.value_min)
                    and new_value < value_min
                )
                or not (isinstance(new_value, int))
            ):
                raise ValueError

        # Validation for strings

        if field_value_type == str:
            if (
                (value_regex := field_config_options.value_regex)
                and not re.search(value_regex, new_value)
            ) or not isinstance(new_value, str):
                raise ValueError

        log.debug(
            "CameraSkybellControllerExtension -> submit_change(): Refreshing settings."
        )

        #
        # Refresh settings data to prime submission payload.
        #

        results = await self.fetch(
            camera_names=[camera_name],
        )

        if not (payload := results[0].raw_attribs) or not (
            (config_id := results[0].config_id) or not isinstance(payload, dict)
        ):
            raise UnexpectedDataStructure("Failed to refresh settings data for device.")

        log.debug(
            "CameraSkybellControllerExtension -> submit_change(): Creating response"
            " payload."
        )

        #
        # Process into response payload.
        #

        # Special processing for ChimeAdjustableVolume (currently only outdoor chime).
        # When volume is set, automatically change on/off setting.

        if isinstance(new_value, self.ChimeAdjustableVolume):
            if new_value == self.ChimeAdjustableVolume.OFF:
                payload.pop(self._FORM_FIELD_OUTDOOR_CHIME_VOLUME, None)
                payload.pop(self._FORM_FIELD_OUTDOOR_CHIME_ONOFF, None)
            else:
                payload[self._FORM_FIELD_OUTDOOR_CHIME_ONOFF] = self.ChimeOnOff.ON.value
                payload[self._FORM_FIELD_OUTDOOR_CHIME_VOLUME] = new_value.value

        # Special processing for ChimeOnOff (currently only indoor chime).
        # Convert enum to str(enum member name)

        elif isinstance(new_value, self.ChimeOnOff):
            if new_value == self.ChimeOnOff.OFF:
                payload.pop(self._FORM_FIELD_INDOOR_CHIME_ONOFF, None)
            else:
                payload[self._FORM_FIELD_INDOOR_CHIME_ONOFF] = self.ChimeOnOff.ON.value

        # Special processing for other enum-based values

        elif issubclass(field_value_type, Enum):
            payload[field_name] = new_value.value

        # Special processing for ints

        elif issubclass(field_value_type, int):
            payload[field_name] = int(new_value)

        # Processing for all else

        else:
            payload[field_name] = new_value

        log.debug(
            "CameraSkybellControllerExtension -> submit_change(): Changing %s to %s.",
            field_name,
            new_value,
        )

        #
        # Add static fields
        #

        processed_payload = self._build_submit_payload(payload)

        #
        # Convert None to ""
        #

        for key, value in processed_payload.items():
            if value is None:
                processed_payload[key] = ""

        #
        # Add static fields.
        #

        debug_payload = processed_payload.copy()
        debug_payload.pop("__VIEWSTATE")

        log.debug(
            "======= POST PAYLOAD - BEGIN =======\n\n%s\n\n======= POST"
            " PAYLOAD - END =======",
            debug_payload,
        )

        #
        # Submit payload and refresh data.
        #

        try:
            async with self._websession.post(
                url=self.ENDPOINT, data=processed_payload, headers=self._headers
            ) as resp:
                text = await resp.text()

                log.debug("Response status: %s", resp.status)

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

        return camera_return_data.settings[slug]

    def _build_submit_payload(  # pylint: disable = no-self-use
        self, response_data: dict
    ) -> dict:
        """Build POST for new setting submission or for getting other camera data."""

        # Pre-populate static fields.
        static_form_data: dict = {
            "__SCROLLPOSITIONX": "0",
            "__SCROLLPOSITIONY": "0",
            "ctl00$phBody$CamSelector$ddlPage": "CameraInfo",
            "ctl00$phBody$AutomaticClipDonationSettings$ShowClipDonationLegalAgreement": (
                "1"
            ),
            "ctl00$phBody$tfSave": "Save",
            "ctl00$phBody$bridgeInfo$wirelessSettings$rblEncryption": "MakeASelection",
            "ctl00$phBody$bridgeInfo$wirelessSettings$rblAlgoritm": "MakeASelection",
            "ctl00$phBody$fwUpgradeModalTailTextBox": (
                "Firmware upgrade is complete. You can check the video device status"
                " after closing this dialog box."
            ),
        }

        # Merge in dynamic fields with changed values.
        static_form_data.update(response_data)

        return static_form_data

    def _extract_fields(
        self, config_id: str, tree: BeautifulSoup
    ) -> ExtendedProperties:
        """Extract data from camera config page."""

        # To prevent a single Skybell error from throwing an exception, missing fields will have values set to empty strings.

        raw_attribs: dict = {}
        properties = ExtendedProperties(
            config_id=config_id,
            settings={},
        )

        try:
            for field_name in self._FORM_FIELDS_BYPASSABLE:
                field = tree.find(attrs={"name": field_name})

                if not field:
                    raw_attribs[field_name] = ""
                else:
                    try:
                        value = extract_field_value(field)
                    except UnexpectedDataStructure:
                        log.warning("Couldn't find field %s", field)
                        value = ""
                    raw_attribs[field_name] = value

            for field_name in self._FORM_FIELDS_GENERIC:
                field = tree.find(attrs={"name": field_name})
                try:
                    value = extract_field_value(field)
                except UnexpectedDataStructure:
                    log.warning("Couldn't find field %s", field)
                    value = ""
                raw_attribs[field_name] = value

            for field_name, property_name in self._FORM_FIELDS_META:
                field = tree.find(attrs={"name": field_name})
                try:
                    value = extract_field_value(field)
                except UnexpectedDataStructure:
                    log.warning("Couldn't find field %s", field)
                    value = ""
                raw_attribs[field_name] = value
                setattr(properties, property_name, value)

            for field_name, config_option in self._form_field_settings:
                field = tree.find(attrs={"name": field_name})

                try:
                    value = extract_field_value(field)
                except UnexpectedDataStructure:
                    log.warning("Couldn't find field %s", field)
                    value = ""

                typed_value: Any

                #
                # CONVERSIONS
                #

                # Convert raw values to enums for ConfigurationOption.current_value.
                # Convert checked/unchecked to str(enum member name) for ConfigurationOption.raw_attribs.

                config_value_type = config_option.value_type
                config_option_type = config_option.option_type

                # Conversions for ChimeOnOff values.

                if config_value_type == self.ChimeOnOff:
                    typed_value = self.ChimeOnOff.ON if value else self.ChimeOnOff.OFF

                    raw_attribs[field_name] = typed_value.value

                # Conversions for slider values.

                if config_value_type in [
                    self.ChimeAdjustableVolume,
                    self.MotionSensitivity,
                ]:
                    raw_attribs[field_name] = value

                    if not value:
                        raise ValueError

                    typed_value = config_value_type(int(value))

                #
                # Conversions for ints.
                #

                # Preprocessing for colors

                if config_option_type == ConfigurationOptionType.COLOR and (
                    value_regex := config_option.value_regex
                ):
                    if not value:
                        raise ValueError

                    match = re.search(value_regex, value)
                    typed_value = str(value)

                    if not match:
                        raise ValueError

                    raw_attribs[field_name] = match.group()

                # Ints

                if config_value_type == int:
                    if not value:
                        raise ValueError

                    typed_value = int(value)
                    raw_attribs[field_name] = typed_value

                # Wrap Up

                config_option.current_value = typed_value

                properties.settings[config_option.slug] = config_option

        except (KeyError, ValueError, UnexpectedDataStructure) as err:
            log.error("Unable to extract field. Failed on field %s.", field_name)
            raise UnexpectedDataStructure from err

        properties.raw_attribs = raw_attribs

        return properties
