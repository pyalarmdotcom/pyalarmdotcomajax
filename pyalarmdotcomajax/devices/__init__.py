"""Alarm.com device base devices."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Protocol, TypedDict, final

import aiohttp

from pyalarmdotcomajax.errors import InvalidConfigurationOption, UnexpectedDataStructure
from pyalarmdotcomajax.extensions import (
    CameraSkybellControllerExtension,
    ConfigurationOption,
)
from pyalarmdotcomajax.helpers import ExtendedEnumMixin

log = logging.getLogger(__name__)


class TroubleCondition(TypedDict):
    """Alarm.com alert / trouble condition."""

    message_id: str
    title: str
    body: str
    device_id: str


class DeviceType(ExtendedEnumMixin):
    """Enum of devices using ADC ids."""

    # Supported
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
    CAMERA = "cameras"
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


DEVICE_URLS: dict = {
    "supported": {
        DeviceType.CAMERA: {
            "relationshipId": "video/camera",
            "endpoint": "{}web/api/video/devices/cameras/{}",
        },
        DeviceType.GARAGE_DOOR: {
            "relationshipId": "devices/garage-door",
            "endpoint": "{}web/api/devices/garageDoors/{}",
        },
        DeviceType.GATE: {
            "relationshipId": "devices/gate",
            "endpoint": "{}web/api/devices/gates/{}",
        },
        DeviceType.IMAGE_SENSOR: {
            "relationshipId": "image-sensor/image-sensor",
            "endpoint": "{}web/api/imageSensor/imageSensors/{}",
            "additional_endpoints": {
                "recent_images": (
                    "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"
                )
            },
        },
        DeviceType.LIGHT: {
            "relationshipId": "devices/light",
            "endpoint": "{}web/api/devices/lights/{}",
        },
        DeviceType.LOCK: {
            "relationshipId": "devices/lock",
            "endpoint": "{}web/api/devices/locks/{}",
        },
        DeviceType.PARTITION: {
            "relationshipId": "devices/partition",
            "endpoint": "{}web/api/devices/partitions/{}",
        },
        DeviceType.SENSOR: {
            "relationshipId": "devices/sensor",
            "endpoint": "{}web/api/devices/sensors/{}",
        },
        DeviceType.SYSTEM: {
            "relationshipId": "systems/system",
            "endpoint": "{}web/api/systems/systems/{}",
        },
        DeviceType.THERMOSTAT: {
            "relationshipId": "devices/thermostat",
            "endpoint": "{}web/api/devices/thermostats/{}",
        },
        DeviceType.WATER_SENSOR: {
            "relationshipId": "devices/water-sensor",
            "endpoint": "{}web/api/devices/waterSensors/{}",
        },
    },
    "unsupported": {
        DeviceType.ACCESS_CONTROL: {
            "relationshipId": "devices/access-control-access-point-device",
            "endpoint": "{}web/api/devices/accessControlAccessPointDevices/{}",
        },
        DeviceType.CAMERA_SD: {
            "relationshipId": "video/sd-card-camera",
            "endpoint": "{}web/api/video/devices/sdCardCameras/{}",
        },
        DeviceType.CAR_MONITOR: {
            "relationshipId": "devices/car-monitor",
            "endpoint": "{}web/api/devices/carMonitors{}",
        },
        DeviceType.COMMERCIAL_TEMP: {
            "relationshipId": "devices/commercial-temperature-sensor",
            "endpoint": "{}web/api/devices/commercialTemperatureSensors/{}",
        },
        # DeviceType.CONFIGURATION: {
        #     "relationshipId": "configuration",
        #     "endpoint": "{}web/api/systems/configurations/{}",
        # },
        # DeviceType.FENCE: {
        #     "relationshipId": "",
        #     "endpoint": "{}web/api/geolocation/fences/{}",
        # },
        DeviceType.GEO_DEVICE: {
            "relationshipId": "geolocation/geo-device",
            "endpoint": "{}web/api/geolocation/geoDevices/{}",
        },
        DeviceType.IQ_ROUTER: {
            "relationshipId": "devices/iq-router",
            "endpoint": "{}web/api/devices/iqRouters/{}",
        },
        DeviceType.REMOTE_TEMP: {
            "relationshipId": "devices/remote-temperature-sensor",
            "endpoint": "{}web/api/devices/remoteTemperatureSensors/{}",
        },
        DeviceType.SCENE: {
            "relationshipId": "automation/scene",
            "endpoint": "{}web/api/automation/scenes/{}",
        },
        DeviceType.SHADE: {
            "relationshipId": "devices/shade",
            "endpoint": "{}web/api/devices/shades/{}",
        },
        DeviceType.SMART_CHIME: {
            "relationshipId": "devices/smart-chime-device",
            "endpoint": "{}web/api/devices/smartChimeDevices/{}",
        },
        DeviceType.SUMP_PUMP: {
            "relationshipId": "devices/sump-pump",
            "endpoint": "{}web/api/devices/sumpPumps/{}",
        },
        DeviceType.SWITCH: {
            "relationshipId": "devices/switch",
            "endpoint": "{}web/api/devices/switches/{}",
        },
        DeviceType.VALVE_SWITCH: {
            "relationshipId": "valve-switch",
            "endpoint": "{}web/api/devices/valveSwitches/{}",
        },
        DeviceType.WATER_METER: {
            "relationshipId": "devices/water-meter",
            "endpoint": "{}web/api/devices/waterMeters/{}",
        },
        DeviceType.WATER_VALVE: {
            "relationshipId": "devices/water-valve",
            "endpoint": "{}web/api/devices/waterValves/{}",
        },
        DeviceType.X10_LIGHT: {
            "relationshipId": "devices/x10light",
            "endpoint": "{}web/api/devices/x10Lights/{}",
        },
    },
}


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


class BaseDevice:
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
    # Casting Functions
    #
    # Functions used for pulling data from _raw_attribs in standardized format.
    @final
    def _get_int(self, key: str) -> int | None:
        """Cast raw value to int. Satisfies mypy."""

        try:
            return int(self._attribs_raw.get(key))  # type: ignore
        except (ValueError, TypeError):
            return None

    @final
    def _get_float(self, key: str) -> int | None:
        """Cast raw value to int. Satisfies mypy."""

        try:
            return float(self._attribs_raw.get(key))  # type: ignore
        except (ValueError, TypeError):
            return None

    @final
    def _get_str(self, key: str) -> str | None:
        """Cast raw value to str. Satisfies mypy."""

        try:
            return str(self._attribs_raw.get(key))
        except (ValueError, TypeError):
            return None

    @final
    def _get_bool(self, key: str) -> bool | None:
        """Cast raw value to bool. Satisfies mypy."""

        if self._attribs_raw.get(key) in [True, False]:
            return self._attribs_raw.get(key)

        return None

    @final
    def _get_list(self, key: str, value_type: type) -> list | None:
        """Cast raw value to list. Satisfies mypy."""

        try:
            duration_list: list = list(self._attribs_raw.get(key))  # type: ignore
            for duration in duration_list:
                value_type(duration)
            return duration_list
        except (ValueError, TypeError):
            pass

        return None

    @final
    def _get_special(self, key: str, value_type: type) -> Any | None:
        """Cast raw value to bool. Satisfies mypy."""

        try:
            return value_type(self._attribs_raw.get(key))
        except (ValueError, TypeError):
            pass

        return None

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
