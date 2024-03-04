"""Skybell HD camera controller extension for Alarm.com."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any

from mashumaro import field_options
from mashumaro.config import BaseConfig

from pyalarmdotcomajax.models.extensions.base import ExtensionAttributes
from pyalarmdotcomajax.models.jsonapi.types import LedColor, RangeInt

FIELD_EVENT_TARGET = "__EVENTTARGET"
FIELD_CONFIG_ID = "ctl00$phBody$CamSelector$ddlCams"


class ChimeAdjustableVolume:
    """Doorbell chime levels for bells with configurable volume."""

    OFF = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class ChimeOnOff:
    """Doorbell chime levels for bells with configurable volume."""

    OFF = "off"
    ON = "on"


class MotionSensitivity:
    """Camera motion sensor sensitivity."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


@dataclass
class SkybellExtensionAttributes(ExtensionAttributes):
    """
    Raw HTML attributes for Skybell HD extension.

    Use exclude_none when dumping!
    """

    # fmt: off

    # Camera Identifiers
    config_id: str = field(metadata=field_options(alias=FIELD_CONFIG_ID))
    _device_name: str = field(metadata=field_options(alias="ctl00$phBody$tbCamName"))

    # Target Attributes
    indoor_chime_state: ChimeOnOff | None = field(metadata=field_options(alias="ctl00$phBody$cbIndoorChime"))
    outdoor_chime_volume: ChimeAdjustableVolume | None = field(metadata=field_options(alias="ctl00$phBody$inpChimeLevel$bootstrapSlider"))
    led_brightness: Annotated[RangeInt, 0, 100] | None = field(metadata=field_options(alias="ctl00$phBody$inpDoorbellLEDIntensity$bootstrapSlider"))
    led_color: LedColor | None = field(metadata=field_options(alias="ctl00$phBody$colorPicker"))
    motion_sensitivity: MotionSensitivity | None = field(metadata=field_options(alias="ctl00$phBody$inpMotionThreshold$bootstrapSlider"))
    _outdoor_chime_state: ChimeOnOff | None = field(metadata=field_options(alias="ctl00$phBody$cbOutdoorChime")) # Not directly configurable. Set through outdoor_chime_volume.

    # Always required for form submission
    _ctl00_ScriptManager1_Hiddenfield: Any
    _VIEWSTATE: Any = field(metadata=field_options(alias="__VIEWSTATE"))
    _VIEWSTATEGENERATOR: Any = field(metadata=field_options(alias="__VIEWSTATEGENERATORy"))
    _VIEWSTATEENCRYPTED: Any = field(metadata=field_options(alias="__VIEWSTATEENCRYPTED"))
    _PREVIOUSPAGE: Any = field(metadata=field_options(alias="__PREVIOUSPAGE"))
    _EVENTVALIDATION: Any = field(metadata=field_options(alias="__EVENTVALIDATION"))
    _ctl00_key: Any = field(metadata=field_options(alias="ctl00$key"))
    _ctl00_phBody_hfRemoteAccessTestResult: Any = field(metadata=field_options(alias="ctl00$phBody$hfRemoteAccessTestResult"))
    _ctl00_phBody_hfAgeLimit: Any = field(metadata=field_options(alias="ctl00$phBody$hfAgeLimit"))
    _ctl00_phBody_AutomaticClipDonationSettings_TextBoxClipQualityComments: Any = field(metadata=field_options(alias="ctl00$phBody$AutomaticClipDonationSettings$TextBoxClipQualityComments"))
    _ctl00_phBody_ddlVideoQuality: Any = field(metadata=field_options(alias="ctl00$phBody$ddlVideoQuality"))
    _ctl00_phBody_ddChimeType: Any = field(metadata=field_options(alias="ctl00$phBody$ddChimeType"))
    _ctl00_phBody_bridgeInfo_tbCamName: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$tbCamName"))
    _ctl00_phBody_bridgeInfo_tbBridgeLogin: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$tbBridgeLogin"))
    _ctl00_phBody_bridgeInfo_tbBridgePwd: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$tbBridgePwd"))
    _ctl00_phBody_bridgeInfo_tbBridgePwdConfirm: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$tbBridgePwdConfirm"))
    _ctl00_phBody_bridgeInfo_hfSelectedDeviceId: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$hfSelectedDeviceId"))
    _ctl00_phBody_bridgeInfo_wirelessSettings_ctl07: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$wirelessSettings$ctl07"))
    _ctl00_phBody_bridgeInfo_wirelessSettings_wirelessShowsBridge: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$wirelessSettings$wirelessShowsBridge"))
    _ctl00_phBody_bridgeInfo_wirelessSettings_txtSSID: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$wirelessSettings$txtSSID"))
    _ctl00_phBody_bridgeInfo_wirelessSettings_ctl05: Any = field(metadata=field_options(alias="ctl00$phBody$bridgeInfo$wirelessSettings$ctl05"))
    _ctl00_phBody_upgradeFirmwareMessageBox: Any = field(metadata=field_options(alias="ctl00$phBody$upgradeFirmwareMessageBox"))

    # Required for form submission only if present.
    _EVENTTARGET: Any = field(default=None, metadata=field_options(alias=FIELD_EVENT_TARGET))
    _EVENTARGUMENT: Any = field(default=None, metadata=field_options(alias="__EVENTARGUMENT"))
    _LASTFOCUS: Any = field(default=None, metadata=field_options(alias="_LASTFOCUS"))

    # fmt: on

    class Config(BaseConfig):
        """Mashumaro configuration."""

        extra = "allow"
        omit_default = True

    @property
    def outdoor_chime_state(self) -> ChimeOnOff | None:
        """
        Outdoor chime state.

        Read only. Set through outdoor_chime_volume.
        """

        return self._outdoor_chime_state

    @property
    def device_name(self) -> str:
        """Camera device name."""

        return self._device_name


# class Skybell(Extension):
#     """Fetcher for Skybell HD config data."""

#     _description = "Adjust indoor and outdoor chimes for Skybell HD video doorbells."

#     _attributes: SkybellExtensionAttributes

#     @property
#     def attributes(self) -> SkybellExtensionAttributes:
#         """Return Skybell HD extension attributes."""

#         return self._attributes
