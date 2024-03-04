"""Controller for Skybell HD cameras."""

from __future__ import annotations

# import asyncio
import logging

# import re
# from dataclasses import fields
# from enum import Enum
# from typing import TYPE_CHECKING, Any
# import aiohttp
# from bs4 import BeautifulSoup, Tag
from pyalarmdotcomajax.const import URL_BASE

# from pyalarmdotcomajax.controllers.base import BaseController
# from pyalarmdotcomajax.exceptions import UnexpectedResponse
# from pyalarmdotcomajax.models.camera import Camera
# from pyalarmdotcomajax.models.extensions.skybell import (
#     FIELD_CONFIG_ID,
#     FIELD_EVENT_TARGET,
#     ChimeAdjustableVolume,
#     ChimeOnOff,
#     SkybellExtensionAttributes,
# )
from pyalarmdotcomajax.models.jsonapi import Resource

# if TYPE_CHECKING:
#     from pyalarmdotcomajax import AlarmBridge


ENDPOINT = f"{URL_BASE}web/Video/SettingsMain_V2.aspx"


log = logging.getLogger(__name__)


# def extract_field_value(field: Tag) -> str:
#     """Extract value from BeautifulSoup4 text, checkbox, and dropdown fields."""

#     # log.debug("Extracting field: %s", field)

#     value = None

#     try:
#         if field.attrs.get("name") and field.name == "select":
#             value = field.findChild(attrs={"selected": "selected"}).attrs["value"]
#         elif field.attrs.get("checked") and field.attrs.get("checked"):
#             value = field.attrs["checked"] == "checked"
#         elif field.attrs.get("value"):
#             value = field.attrs["value"]

#     except (KeyError, AttributeError) as err:
#         raise ValueError from err

#     if not value:
#         raise ValueError("Value not found.")

#     return str(value)


def is_skybell(resource: Resource) -> bool:
    """Check if resource is a Skybell camera."""

    return resource.attributes.get("deviceModel") == "SKYBELLHD"


# class SkybellExtensionController(BaseController):
#     """Fetcher for Skybell HD config data."""

#     def __init__(self, bridge: AlarmBridge, cameras: dict[str, Camera]) -> None:
#         """Initialize extension."""

#         super().__init__()

#         self._bridge = bridge

#         self._cameras = cameras

#         self._resources: dict[str, SkybellExtensionAttributes] = {}  # Camera NAME, not ID

#     async def fetch(
#         self,
#         camera_ids: list[str] | None = None,
#     ) -> None:
#         """Retrieve updated configuration data for specified devices."""

#         camera_names = [self._cameras[camera_id].name for camera_id in camera_ids] if camera_ids else None

#         #
#         # Initialize request variables and get data for first camera.
#         #

#         new_resources: dict[str, SkybellExtensionAttributes] = {}  # Camera NAME, not ID
#         retrieval_queue: list[str] = []  # Camera config ID

#         try:
#             async with self._bridge.create_request("get", ENDPOINT) as resp:
#                 text = await resp.text()
#                 log.debug("Response status from Alarm.com: %s", resp.status)
#                 # log.debug("Response text from Alarm.com: %s", text)
#                 tree = BeautifulSoup(text, "html.parser")

#                 # Build list of cameras to retrieve data for.

#                 child: Tag
#                 for child in tree.select_one("#ctl00_phBody_CamSelector_ddlCams").findChildren():
#                     camera_config_id: str = child.attrs.get("value")
#                     if child.attrs.get("selected") == "selected":
#                         # Retrieve data for camera on current page.
#                         first_camera_attributes = self._extract_fields(camera_config_id, tree)

#                         if (camera_names is None) or (child.text in camera_names):
#                             # Store data for current camera.
#                             new_resources[first_camera_attributes.device_name] = first_camera_attributes
#                     else:
#                         # Add to camera config retrieval queue
#                         retrieval_queue.append(camera_config_id)

#         except (TimeoutError, aiohttp.ClientError, asyncio.exceptions.CancelledError):
#             log.exception("Can not load settings page from Alarm.com")
#             raise
#         except (AttributeError, IndexError) as err:
#             log.exception("Unable to extract page info from Alarm.com.")
#             log.debug("====== HTTP DUMP BEGIN ======\n%s\n====== HTTP DUMP END ======", text)
#             raise UnexpectedResponse from err

#         #
#         # Get data for additional cameras.
#         #
#         try:
#             for config_id in retrieval_queue:
#                 # Build payload to request config page for next camera

#                 if not (postback_form_data := first_camera_attributes.to_dict()):
#                     raise UnexpectedResponse

#                 postback_form_data[FIELD_EVENT_TARGET] = FIELD_CONFIG_ID
#                 postback_form_data[FIELD_CONFIG_ID] = config_id

#                 async with self._bridge.create_request(
#                     "post", url=ENDPOINT, data=SkybellExtensionAttributes.from_dict(postback_form_data)
#                 ) as resp:
#                     text = await resp.text()
#                     log.debug("Response status from Alarm.com: %s", resp.status)
#                     tree = BeautifulSoup(text, "html.parser")

#                     # Pull data for camera on current page
#                     iter_camera_attributes = self._extract_fields(config_id, tree)
#                     new_resources[iter_camera_attributes.device_name] = iter_camera_attributes

#         except (TimeoutError, aiohttp.ClientError, asyncio.exceptions.CancelledError):
#             log.exception("Can not load settings page for additional camera from Alarm.com")
#             raise
#         except UnexpectedResponse:
#             log.debug("HTTP Response Status %s, Body:\n%s", resp.status, text)
#             raise

#         return camera_return_data

#     async def submit_change(
#         self,
#         camera_name: str,
#         slug: str,
#         new_value: Any,
#     ) -> ExtendedPropertyAttributes:
#         """Change a setting."""

#         # For non-volume adjustable chimes (indoor), value is "on" when checkbox is checked. Field is removed from POST payload when off.
#         # For volume adjustable chimes (outdoor),  When on, either 1 for low, 2 for medium, 3 for high, or 0 for off.

#         log.debug(
#             "CameraSkybellControllerExtension -> submit_change(): Requested change for %s: %s to %s.",
#             camera_name,
#             slug,
#             new_value,
#         )

#         #
#         # Get field name for submitted value.
#         #

#         field_name: str
#         field_value_type: type
#         field_config_options: ExtendedPropertyAttributes

#         try:
#             for config_option_field_name, config_option in self._form_field_settings:
#                 if config_option.slug == slug:
#                     field_name = config_option_field_name
#                     field_value_type = config_option.value_type
#                     field_config_options = config_option

#         except KeyError as err:
#             raise UnexpectedResponse("Slug not found.") from err

#         log.debug("CameraSkybellControllerExtension -> submit_change(): Validating input.")

#         #
#         # VALIDATE INPUT
#         #

#         # Check that submitted value is correct type.
#         # Currently only supports enums. In the future, should be expanded to also support native types.

#         if field_value_type and not isinstance(new_value, field_value_type):
#             raise TypeError(f"New value {new_value} is not of type {field_value_type}")

#         # Validation for ints

#         if field_value_type == int and (
#             ((value_max := field_config_options.value_max) and new_value > value_max)
#             or ((value_min := field_config_options.value_min) and new_value < value_min)
#             or not (isinstance(new_value, int))
#         ):
#             raise ValueError

#         # Validation for strings

#         if field_value_type == str and (
#             ((value_regex := field_config_options.value_regex) and not re.search(value_regex, new_value))
#             or not isinstance(new_value, str)
#         ):
#             raise ValueError

#         log.debug("CameraSkybellControllerExtension -> submit_change(): Refreshing settings.")

#         #
#         # Refresh settings data to prime submission payload.
#         #

#         results = await fetch(
#             camera_names=[camera_name],
#         )

#         if not (payload := results[0].raw_attribs) or not (
#             (config_id := results[0].config_id) or not isinstance(payload, dict)
#         ):
#             raise UnexpectedResponse("Failed to refresh settings data for device.")

#         log.debug("CameraSkybellControllerExtension -> submit_change(): Creating response payload.")

#         #
#         # Process into response payload.
#         #

#         # Special processing for ChimeAdjustableVolume (currently only outdoor chime).
#         # When volume is set, automatically change on/off setting.

#         if isinstance(new_value, ChimeAdjustableVolume):
#             if new_value == ChimeAdjustableVolume.OFF:
#                 payload.pop(FORM_FIELD_OUTDOOR_CHIME_VOLUME, None)
#                 payload.pop(FORM_FIELD_OUTDOOR_CHIME_ONOFF, None)
#             else:
#                 payload[FORM_FIELD_OUTDOOR_CHIME_ONOFF] = ChimeOnOff.ON.value
#                 payload[FORM_FIELD_OUTDOOR_CHIME_VOLUME] = new_value.value

#         # Special processing for ChimeOnOff (currently only indoor chime).
#         # Convert enum to str(enum member name)

#         elif isinstance(new_value, ChimeOnOff):
#             if new_value == ChimeOnOff.OFF:
#                 payload.pop(FORM_FIELD_INDOOR_CHIME_ONOFF, None)
#             else:
#                 payload[FORM_FIELD_INDOOR_CHIME_ONOFF] = ChimeOnOff.ON.value

#         # Special processing for other enum-based values

#         elif issubclass(field_value_type, Enum):
#             payload[field_name] = new_value.value

#         # Special processing for ints

#         elif issubclass(field_value_type, int):
#             payload[field_name] = int(new_value)

#         # Processing for all else

#         else:
#             payload[field_name] = new_value

#         log.debug(
#             "CameraSkybellControllerExtension -> submit_change(): Changing %s to %s.",
#             field_name,
#             new_value,
#         )

#         #
#         # Add static fields
#         #

#         processed_payload = self._build_submit_payload(payload)

#         #
#         # Convert None to ""
#         #

#         for key, value in processed_payload.items():
#             if value is None:
#                 processed_payload[key] = ""

#         #
#         # Add static fields.
#         #

#         debug_payload = processed_payload.copy()
#         debug_payload.pop("__VIEWSTATE")

#         log.debug(
#             "======= POST PAYLOAD - BEGIN =======\n\n%s\n\n======= POST PAYLOAD - END =======",
#             debug_payload,
#         )

#         #
#         # Submit payload and refresh data.
#         #

#         try:
#             async with _websession.post(url=ENDPOINT, data=processed_payload, headers=_headers) as resp:
#                 text = await resp.text()

#                 log.debug("Response status: %s", resp.status)

#                 tree = BeautifulSoup(text, "html.parser")

#                 # Pull data for camera on current page
#                 camera_return_data = self._extract_fields(config_id, tree)

#         except (TimeoutError, aiohttp.ClientError, asyncio.exceptions.CancelledError):
#             log.exception("Can not load settings page for additional camera from Alarm.com")
#             raise

#         return camera_return_data.settings[slug]

#     def _build_submit_payload(self, response_data: dict) -> dict:
#         """Build POST for new setting submission or for getting other camera data."""

#         # Pre-populate static fields.
#         static_form_data: dict = {
#             "__SCROLLPOSITIONX": "0",
#             "__SCROLLPOSITIONY": "0",
#             "ctl00$phBody$CamSelector$ddlPage": "CameraInfo",
#             "ctl00$phBody$AutomaticClipDonationSettings$ShowClipDonationLegalAgreement": "1",
#             "ctl00$phBody$tfSave": "Save",
#             "ctl00$phBody$bridgeInfo$wirelessSettings$rblEncryption": "MakeASelection",
#             "ctl00$phBody$bridgeInfo$wirelessSettings$rblAlgoritm": "MakeASelection",
#             "ctl00$phBody$fwUpgradeModalTailTextBox": (
#                 "Firmware upgrade is complete. You can check the video device status after closing this dialog"
#                 " box."
#             ),
#         }

#         # Merge in dynamic fields with changed values.
#         static_form_data.update(response_data)

#         return static_form_data

#     def _extract_fields(self, config_id: str, tree: BeautifulSoup) -> SkybellExtensionAttributes:
#         """Extract data from camera config page."""

#         extracted_fields: dict[str, Any] = {}

#         # Use aliases in SkybellExtensionAttributes to build list of fields to fetch.
#         # To prevent a single Skybell error from throwing an exception, missing fields will have values set to empty strings.

#         for field_name in fields(SkybellExtensionAttributes):
#             if alias := field_name.metadata.get("alias"):
#                 try:
#                     extracted_fields[alias] = (
#                         extract_field_value(alias) if tree.find(attrs={"name": alias}) else ""
#                     )
#                 except ValueError:
#                     log.warning("Couldn't find field %s", alias)

#         return SkybellExtensionAttributes.from_dict(extracted_fields)
