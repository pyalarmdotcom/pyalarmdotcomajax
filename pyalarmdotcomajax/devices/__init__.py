"""Alarm.com device base devices."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Protocol, TypedDict

import aiohttp

from pyalarmdotcomajax.errors import InvalidConfigurationOption, UnexpectedDataStructure
from pyalarmdotcomajax.extensions import (
    CameraSkybellControllerExtension,
    ConfigurationOption,
)
from pyalarmdotcomajax.helpers import CastingMixin, ExtendedEnumMixin

log = logging.getLogger(__name__)


class DeviceType(ExtendedEnumMixin):
    """Enum of devices using ADC ids."""

    # Supported
    CAMERA = "cameras"
    GARAGE_DOOR = "garageDoors"
    GATE = "gates"
    IMAGE_SENSOR = "imageSensors"
    LIGHT = "lights"
    LOCK = "locks"
    PARTITION = "partitions"
    SENSOR = "sensors"
    SYSTEM = "systems"
    THERMOSTAT = "thermostats"
    WATER_SENSOR = "waterSensors"

    # Unsupported
    ACCESS_CONTROL = "accessControlAccessPointDevices"
    CAMERA_SD = "sdCardCameras"
    CAR_MONITOR = "carMonitors"
    COMMERCIAL_TEMP = "commercialTemperatureSensors"
    # CONFIGURATION = "configuration"
    # FENCE = "fences"
    GEO_DEVICE = "geoDevices"
    IQ_ROUTER = "iqRouters"
    REMOTE_TEMP = "remoteTemperatureSensors"
    SCENE = "scenes"
    SHADE = "shades"
    SMART_CHIME = "smartChimeDevices"
    SUMP_PUMP = "sumpPumps"
    SWITCH = "switches"
    VALVE_SWITCH = "valveSwitches"
    WATER_METER = "waterMeters"
    WATER_VALVE = "waterValves"
    X10_LIGHT = "x10Lights"


class DeviceUrlMetadata(TypedDict, total=False):
    """Stores device URL metadata."""

    primary: str
    additional: dict[str, str]


DEVICE_ENDPOINTS: dict[DeviceType, DeviceUrlMetadata] = {
    DeviceType.CAMERA: DeviceUrlMetadata(primary="{}web/api/video/devices/cameras/{}"),
    DeviceType.GARAGE_DOOR: DeviceUrlMetadata(
        primary="{}web/api/devices/garageDoors/{}"
    ),
    DeviceType.GATE: DeviceUrlMetadata(primary="{}web/api/devices/gates/{}"),
    DeviceType.IMAGE_SENSOR: DeviceUrlMetadata(
        primary="{}web/api/imageSensor/imageSensors/{}",
        additional={
            "recent_images": (
                "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"
            )
        },
    ),
    DeviceType.LIGHT: DeviceUrlMetadata(primary="{}web/api/devices/lights/{}"),
    DeviceType.LOCK: DeviceUrlMetadata(primary="{}web/api/devices/locks/{}"),
    DeviceType.PARTITION: DeviceUrlMetadata(primary="{}web/api/devices/partitions/{}"),
    DeviceType.SENSOR: DeviceUrlMetadata(primary="{}web/api/devices/sensors/{}"),
    DeviceType.SYSTEM: DeviceUrlMetadata(primary="{}web/api/systems/systems/{}"),
    DeviceType.THERMOSTAT: DeviceUrlMetadata(
        primary="{}web/api/devices/thermostats/{}"
    ),
    DeviceType.WATER_SENSOR: DeviceUrlMetadata(
        primary="{}web/api/devices/waterSensors/{}"
    ),
    DeviceType.ACCESS_CONTROL: DeviceUrlMetadata(
        primary="{}web/api/devices/accessControlAccessPointDevices/{}"
    ),
    DeviceType.CAMERA_SD: DeviceUrlMetadata(
        primary="{}web/api/video/devices/sdCardCameras/{}"
    ),
    DeviceType.CAR_MONITOR: DeviceUrlMetadata(
        primary="{}web/api/devices/carMonitors/{}"
    ),
    DeviceType.COMMERCIAL_TEMP: DeviceUrlMetadata(
        primary="{}web/api/devices/commercialTemperatureSensors/{}"
    ),
    # DeviceType.CONFIGURATION: DeviceUrlMetadata(primary="{}web/api/systems/configurations/{}"),
    # DeviceType.FENCE: DeviceUrlMetadata(primary="{}web/api/geolocation/fences/{}"),
    DeviceType.GEO_DEVICE: DeviceUrlMetadata(
        primary="{}web/api/geolocation/geoDevices/{}"
    ),
    DeviceType.IQ_ROUTER: DeviceUrlMetadata(primary="{}web/api/devices/iqRouters/{}"),
    DeviceType.REMOTE_TEMP: DeviceUrlMetadata(
        primary="{}web/api/devices/remoteTemperatureSensors/{}"
    ),
    DeviceType.SCENE: DeviceUrlMetadata(primary="{}web/api/automation/scenes/{}"),
    DeviceType.SHADE: DeviceUrlMetadata(primary="{}web/api/devices/shades/{}"),
    DeviceType.SMART_CHIME: DeviceUrlMetadata(
        primary="{}web/api/devices/smartChimeDevices/{}"
    ),
    DeviceType.SUMP_PUMP: DeviceUrlMetadata(primary="{}web/api/devices/sumpPumps/{}"),
    DeviceType.SWITCH: DeviceUrlMetadata(primary="{}web/api/devices/switches/{}"),
    DeviceType.VALVE_SWITCH: DeviceUrlMetadata(
        primary="{}web/api/devices/valveSwitches/{}"
    ),
    DeviceType.WATER_METER: DeviceUrlMetadata(
        primary="{}web/api/devices/waterMeters/{}"
    ),
    DeviceType.WATER_VALVE: DeviceUrlMetadata(
        primary="{}web/api/devices/waterValves/{}"
    ),
    DeviceType.X10_LIGHT: DeviceUrlMetadata(primary="{}web/api/devices/x10Lights/{}"),
}

DEVICE_REL_IDS: dict = {
    DeviceType.CAMERA: "video/camera",
    DeviceType.GARAGE_DOOR: "devices/garage-door",
    DeviceType.GATE: "devices/gate",
    DeviceType.IMAGE_SENSOR: "image-sensor/image-sensor",
    DeviceType.LIGHT: "devices/light",
    DeviceType.LOCK: "devices/lock",
    DeviceType.PARTITION: "devices/partition",
    DeviceType.SENSOR: "devices/sensor",
    DeviceType.SYSTEM: "systems/system",
    DeviceType.THERMOSTAT: "devices/thermostat",
    DeviceType.WATER_SENSOR: "devices/water-sensor",
    DeviceType.ACCESS_CONTROL: "devices/access-control-access-point-device",
    DeviceType.CAMERA_SD: "video/sd-card-camera",
    DeviceType.CAR_MONITOR: "devices/car-monitor",
    DeviceType.COMMERCIAL_TEMP: "devices/commercial-temperature-sensor",
    # DeviceType.CONFIGURATION: "configuration",
    # DeviceType.FENCE: "",
    DeviceType.GEO_DEVICE: "geolocation/geo-device",
    DeviceType.IQ_ROUTER: "devices/iq-router",
    DeviceType.REMOTE_TEMP: "devices/remote-temperature-sensor",
    DeviceType.SCENE: "automation/scene",
    DeviceType.SHADE: "devices/shade",
    DeviceType.SMART_CHIME: "devices/smart-chime-device",
    DeviceType.SUMP_PUMP: "devices/sump-pump",
    DeviceType.SWITCH: "devices/switch",
    DeviceType.VALVE_SWITCH: "valve-switch",
    DeviceType.WATER_METER: "devices/water-meter",
    DeviceType.WATER_VALVE: "devices/water-valve",
    DeviceType.X10_LIGHT: "devices/x10-light",
}


SUPPORTED_DEVICES = [
    DeviceType.CAMERA,
    DeviceType.GARAGE_DOOR,
    DeviceType.GATE,
    DeviceType.IMAGE_SENSOR,
    DeviceType.LIGHT,
    DeviceType.LOCK,
    DeviceType.PARTITION,
    DeviceType.SENSOR,
    DeviceType.SYSTEM,
    DeviceType.THERMOSTAT,
    DeviceType.WATER_SENSOR,
]
UNSUPPORTED_DEVICES = [
    DeviceType.ACCESS_CONTROL,
    DeviceType.CAMERA_SD,
    DeviceType.CAR_MONITOR,
    DeviceType.COMMERCIAL_TEMP,
    # DeviceType.CONFIGURATION,
    # DeviceType.FENCE,
    DeviceType.GEO_DEVICE,
    DeviceType.IQ_ROUTER,
    DeviceType.REMOTE_TEMP,
    DeviceType.SCENE,
    DeviceType.SHADE,
    DeviceType.SMART_CHIME,
    DeviceType.SUMP_PUMP,
    DeviceType.SWITCH,
    DeviceType.VALVE_SWITCH,
    DeviceType.WATER_METER,
    DeviceType.WATER_VALVE,
    DeviceType.X10_LIGHT,
]

ALL_DEVICE_TYPES = SUPPORTED_DEVICES + UNSUPPORTED_DEVICES


class TroubleCondition(TypedDict):
    """Alarm.com alert / trouble condition."""

    message_id: str
    title: str
    body: str
    device_id: str


class DesiredStateProtocol(Protocol):
    """Private variables for DesiredStateMixin."""

    _attribs_raw: dict
    desired_state: Enum | None
    has_state: bool
    state: Enum | None
    DeviceState: type[Enum]


class DesiredStateMixin:
    """Mixin decorator for entities with desired_state attribute."""

    @property
    def desired_state(self: DesiredStateProtocol) -> Enum | None:
        """Return state."""

        try:
            state: Enum = self.DeviceState(self._attribs_raw.get("desiredState"))
        except (ValueError, TypeError):
            return None

        return state


class ElementSpecificData(TypedDict, total=False):
    """Hold entity-type-specific metadata."""

    raw_recent_images: set[dict]


class BaseDevice(CastingMixin):
    """Contains properties shared by all ADC devices."""

    DEVICE_MODELS: dict  # deviceModelId: {"manufacturer": str, "model": str}

    def __init__(
        self,
        id_: str,
        send_action_callback: Callable,
        config_change_callback: Callable | None,
        subordinates: list,
        raw_device_data: dict,
        element_specific_data: ElementSpecificData | None = None,
        trouble_conditions: list | None = None,
        partition_id: str | None = None,
        settings: dict | None = None,  # slug: ConfigurationOption
    ) -> None:
        """Initialize base element class."""

        self._id_: str = id_
        self._family_raw: str | None = raw_device_data.get("type")
        self._attribs_raw: dict = raw_device_data.get("attributes", {})
        self._element_specific_data: ElementSpecificData = (
            element_specific_data if element_specific_data else {}
        )
        self._send_action_callback: Callable = send_action_callback
        self._config_change_callback: Callable | None = config_change_callback
        self._subordinates: list = subordinates
        self._settings: dict = settings if settings else {}

        self.trouble_conditions: list[TroubleCondition] = (
            trouble_conditions if trouble_conditions else []
        )

        self._system_id: str | None = (
            raw_device_data.get("relationships", {})
            .get("system", {})
            .get("data", {})
            .get("id")
        )
        self._partition_id: str | None = partition_id

        self.process_element_specific_data()

        log.debug("Initialized %s %s", self._family_raw, self.name)

    #
    # Properties
    #

    @property
    def read_only(self) -> bool | None:
        """Return whether logged in user has permission to change state."""
        return (
            not result
            if isinstance(
                (result := self._attribs_raw.get("hasPermissionToChangeState")),
                bool,
            )
            else None
        )

    @property
    def id_(self) -> str:
        """Return device ID."""
        return self._id_

    @property
    def name(self) -> None | str:
        """Return user-assigned device name."""

        return self._attribs_raw.get("description", None)

    @property
    def has_state(self) -> bool:
        """Return whether entity reports state."""
        return self._attribs_raw.get("hasState", False)

    @property
    def state(self) -> Enum | None:
        """Return state."""

        try:
            state = self.DeviceState(self._attribs_raw.get("state"))
        except ValueError:
            return None

        return state

    @property
    def settings(self) -> dict:
        """Return user-changable settings."""

        return {
            config_option.slug: config_option
            for config_option in self._settings.values()
            if isinstance(config_option, ConfigurationOption)
            and config_option.user_configurable
        }

    @property
    def battery_low(self) -> bool | None:
        """Return whether battery is low."""
        return self._attribs_raw.get("lowBattery")

    @property
    def battery_critical(self) -> bool | None:
        """Return whether battery is critically low."""
        return self._attribs_raw.get("criticalBattery")

    @property
    def system_id(self) -> str | None:
        """Return ID of device's parent system."""
        return self._system_id

    @property
    def partition_id(self) -> str | None:
        """Return ID of device's parent partition."""
        return self._partition_id

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return self._attribs_raw.get("isMalfunctioning", True) or self.state is None

    @property
    def mac_address(self) -> bool | None:
        """Return device MAC address."""
        return self._attribs_raw.get("macAddress")

    @property
    def raw_state_text(self) -> str | None:
        """Return state description as reported by ADC."""
        return self._attribs_raw.get("displayStateText")

    @property
    def model_text(self) -> str | None:
        """Return device model as reported by ADC."""
        return (
            reported_model
            if (reported_model := self._attribs_raw.get("deviceModel"))
            else self.DEVICE_MODELS.get(self._attribs_raw.get("deviceModelId"))
        )

    @property
    def manufacturer(self) -> str | None:
        """Return device model as reported by ADC."""
        return self._attribs_raw.get("manufacturer")

    @property
    def debug_data(self) -> dict:
        """Return data that is helpful for debugging."""
        return self._attribs_raw

    @property
    def device_subtype(self) -> Enum | None:
        """Return normalized device subtype const. E.g.: contact, glass break, etc."""
        try:
            return self.Subtype(self._attribs_raw["deviceType"])
        except (ValueError, KeyError):
            return None

    # #
    # PLACEHOLDERS
    # #

    # All subclasses will have above functions. Only some will have the below and must be implemented as overloads.
    # Methods below are included here to silence mypy errors.

    class DeviceState(Enum):
        """Hold device state values. To be overridden by children."""

    class Command(Enum):
        """Hold device commands. To be overridden by children."""

    class Subtype(Enum):
        """Hold device subtypes. To be overridden by children."""

    @dataclass
    class DeviceAttributes:
        """Hold non-primary device state attributes. To be overridden by children."""

    @property
    def attributes(self) -> DeviceAttributes | None:
        """Hold non-primary device state attributes. To be overridden by children."""

    @property
    def desired_state(self) -> Enum | None:
        """Return state. To be overridden by children."""

    def process_element_specific_data(self) -> None:
        """Process element specific data. To be overridden by children."""

        return None

    async def async_change_setting(self, slug: str, new_value: Any) -> None:
        """Update specified configuration setting via extension."""

        if not self._config_change_callback:
            log.error(
                (
                    "async_change_setting called for %s, which does not have a"
                    " config_change_callback set."
                ),
                self.name,
            )
            return

        config_option: ConfigurationOption | None = self.settings.get(slug)
        extension: type[CameraSkybellControllerExtension] | None = (
            config_option.extension if config_option else None
        )

        if not extension:
            raise InvalidConfigurationOption

        log.debug(
            (
                "BaseDevice -> async_change_setting: Calling change setting function"
                " for %s %s (%s) via extension %s."
            ),
            type(self).__name__,
            self.name,
            self.id_,
            extension,
        )

        try:
            updated_option = await self._config_change_callback(
                camera_name=self.name, slug=slug, new_value=new_value
            )
        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
            asyncio.exceptions.CancelledError,
        ) as err:
            raise err
        except UnexpectedDataStructure as err:
            raise err

        self._settings["slug"] = updated_option

    # #
    # CASTING FUNCTIONS
    # #

    # Override CastingMixin functions to automatically pass in _raw_attribs dict.

    def _get_int(self, key: str) -> int | None:
        """Return int value from _attribs_raw."""
        return super()._safe_int_from_dict(self._attribs_raw, key)

    def _get_float(self, key: str) -> float | None:
        """Return float value from _attribs_raw."""
        return super()._safe_float_from_dict(self._attribs_raw, key)

    def _get_str(self, key: str) -> str | None:
        """Return str value from _attribs_raw."""
        return super()._safe_str_from_dict(self._attribs_raw, key)

    def _get_bool(self, key: str) -> bool | None:
        """Return bool value from _attribs_raw."""
        return super()._safe_bool_from_dict(self._attribs_raw, key)

    def _get_list(self, key: str, value_type: type) -> list | None:
        """Return list value from _attribs_raw."""
        return super()._safe_list_from_dict(self._attribs_raw, key, value_type)

    def _get_special(self, key: str, value_type: type) -> Any | None:
        """Return specified type value from _attribs_raw."""
        return super()._safe_special_from_dict(self._attribs_raw, key, value_type)
