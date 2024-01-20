"""Alarm.com device base devices."""

from __future__ import annotations

import contextlib
import logging
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, Optional, TypedDict

from pyalarmdotcomajax.const import ATTR_DESIRED_STATE, ATTR_STATE
from pyalarmdotcomajax.exceptions import (
    InvalidConfigurationOption,
)
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


class BatteryState(Enum):
    """Enum of device battery states."""

    NO_BATTERY = 0
    NORMAL = 1
    LOW = 2
    CRITICAL = 3


class TroubleCondition(TypedDict):
    """Alarm.com alert / trouble condition."""

    message_id: str
    title: str
    body: str
    device_id: str


class DeviceTypeSpecificData(TypedDict, total=False):
    """Hold entity-type-specific metadata."""

    raw_recent_images: list[dict]


class UserProfile(TypedDict):
    """Hold user profile fields required by devices."""

    uses_celsius: bool


class BaseDevice(ABC, CastingMixin):
    """Contains properties shared by all ADC hardware devices."""

    def __init__(
        self,
        id_: str,
        send_action_callback: Callable,
        config_change_callback: Callable | None,
        children: list[tuple[str, DeviceType]],
        raw_device_data: dict,
        user_profile: UserProfile,
        device_type_specific_data: DeviceTypeSpecificData | None = None,
        trouble_conditions: list | None = None,
        partition_id: str | None = None,
        settings: dict | None = None,  # slug: ConfigurationOption
    ) -> None:
        """Initialize base element class."""

        self.id_: Final[str] = id_

        self._raw: dict = raw_device_data

        self._send_action_callback = send_action_callback

        self.external_update_callback: list[tuple[Callable, Optional[str]]] = []

        self._device_type_specific_data: DeviceTypeSpecificData = (
            device_type_specific_data if device_type_specific_data else {}
        )
        self._settings: dict = settings if settings else {}
        self._partition_id: str | None = partition_id
        self._user_profile: UserProfile = user_profile

        self.children = children
        self.trouble_conditions: list[TroubleCondition] = trouble_conditions if trouble_conditions else []

        self._config_change_callback: Callable | None = config_change_callback

        self.process_device_type_specific_data()

        log.debug("Initialized %s %s", raw_device_data.get("type"), self.name)

    #
    # Properties
    #

    @property
    def attributes(self) -> DeviceAttributes | None:
        """Hold non-primary device state attributes. To be overridden by children."""

    @property
    def raw_attributes(self) -> dict:
        """Return raw attributes."""

        return dict(self._raw.get("attributes", {}))

    @property
    def system_id(self) -> str | None:
        """Return ID of device's parent system."""

        if sys := self._raw.get("relationships", {}).get("system", {}).get("data", {}).get("id"):
            return str(sys)

        return None

    @property
    def debug_data(self) -> dict:
        """Return data that is helpful for debugging."""
        return self.raw_attributes

    @property
    def name(self) -> str:
        """Return user-assigned device name."""

        return str(self.raw_attributes["description"])

    @property
    def models(self) -> dict:
        """Return mapping of known ADC model IDs to manufacturer and model name. To be overridden by children."""

        return {}  # deviceModelId: {"manufacturer": str, "model": str}

    @property
    def read_only(self) -> bool | None:
        """Return whether logged in user has permission to change state."""
        return (
            not result
            if isinstance(
                (result := self.raw_attributes.get("hasPermissionToChangeState")),
                bool,
            )
            else None
        )

    @property
    def available(self) -> bool:
        """Return whether the light can be manipulated."""
        return not self.malfunction

    @property
    def has_state(self) -> bool | None:
        """Return whether entity reports state."""

        return self.raw_attributes.get("hasState")

    @property
    def state(self) -> DeviceState | None:
        """Return state."""

        # Devices that don't report state on Alarm.com (i.e.: Smoke Detectors, phones, etc.) still have a value in the state field.
        # Scenes do not have state at all.
        if self.has_state:
            with contextlib.suppress(ValueError):
                return self.DeviceState(self.raw_attributes.get("state"))

        return None

    @property
    def desired_state(self) -> DeviceState | None:
        """Return state."""

        # Devices that don't report state on Alarm.com (i.e.: Smoke Detectors, phones, etc.) still have a value in the state field.
        # Scenes do not have state at all.
        if self.has_state:
            with contextlib.suppress(ValueError, KeyError):
                return self.DeviceState(self.raw_attributes.get("desiredState"))

        return None

    @property
    def settings(self) -> dict:
        """Return user-changable settings."""

        return {
            config_option.slug: config_option
            for config_option in self._settings.values()
            if isinstance(config_option, ConfigurationOption) and config_option.user_configurable
        }

    @property
    def battery_low(self) -> bool | None:
        """Return whether battery is low."""

        # TODO: Deprecate in v1.0.0. Replaced by battery_state.

        return self.raw_attributes.get("lowBattery")

    @property
    def battery_critical(self) -> bool | None:
        """Return whether battery is critically low."""

        # TODO: Deprecate in v1.0.0. Replaced by battery_state.

        return self.raw_attributes.get("criticalBattery")

    @property
    def battery_state(self) -> BatteryState:
        """Return battery state."""

        try:
            if self.raw_attributes["criticalBattery"]:
                return BatteryState.CRITICAL
            if self.raw_attributes["lowBattery"]:
                return BatteryState.LOW
        except KeyError:
            return BatteryState.NO_BATTERY
        else:
            return BatteryState.NORMAL

    @property
    def partition_id(self) -> str | None:
        """Return ID of device's parent partition."""
        return self._partition_id

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return self.raw_attributes.get("isMalfunctioning")

    @property
    def mac_address(self) -> str | None:
        """Return device MAC address."""
        return str(self.raw_attributes.get("macAddress"))

    @property
    def raw_state_text(self) -> str | None:
        """Return state description as reported by ADC."""
        return str(self.raw_attributes.get("displayStateText"))

    @property
    def model_text(self) -> str:
        """Return device model as reported by ADC."""

        if model := self.raw_attributes.get("deviceModel"):
            return str(model)

        if model := self.models.get(self.raw_attributes.get("deviceModelId")):
            return str(model)

        return ""

    @property
    def manufacturer(self) -> str | None:
        """Return device model as reported by ADC."""
        return self.raw_attributes.get("manufacturer")

    @property
    def device_subtype(self) -> Enum | None:
        """Return normalized device subtype const. E.g.: contact, glass break, etc."""
        try:
            return self.Subtype(self.raw_attributes.get("deviceType"))
        except (ValueError, TypeError):
            return None

    # #
    # FUNCTIONS
    # #

    async def _send_action(
        self,
        device_type: DeviceType,
        event: BaseDevice.Command,
        device_id: str,
        msg_body: dict | None = None,
        retry_on_failure: bool = True,
    ) -> None:
        """Send action to ADC."""

        if msg_body is None:
            msg_body = {}
        if updated_device_object := await self._send_action_callback(
            device_type, event, device_id, msg_body, retry_on_failure
        ):
            try:
                await self.async_handle_external_attribute_change(
                    updated_device_object["data"]["attributes"], "user action response"
                )
            except KeyError:
                log.exception(f"Failed to update device {self.name} with response {updated_device_object}")

    async def async_handle_external_attribute_change(
        self, new_attributes: dict, source: str | None = None
    ) -> None:
        """Update device attribute when notified of externally-triggered change."""

        log.info(
            f"{__name__} Got update for {self.name} ({self.id_}){' from ' + source if source else ''} with"
            f" new {new_attributes}."
        )

        self._raw.setdefault("attributes", {}).update(new_attributes)

        if log.level == logging.DEBUG:
            log_str = ""
            for key, value in new_attributes.items():
                if (current_value := self.raw_attributes.get(key)) != value:
                    log_str += f" | {str(key).upper()}:: [{current_value}] -> [{value}]"
            if log_str:
                log.debug(f"ATTRIBUTE NAME:: Current_Value -> Desired_Value{log_str}")

        # for external_callback, listener_name in self.external_update_callback:
        for external_callback, _ in self.external_update_callback:
            # Trace logging for @catellie
            # log.debug(
            #     f"{__name__} Calling external update callback for listener {listener_name or 'Main'} by"
            #     f" {self.name} ({self.id_})"
            # )

            external_callback()

    def register_external_update_callback(self, callback: Callable, listener_name: str | None = None) -> None:
        """Register callback to be called when device state changes."""

        # Trace logging for @catellie
        # log.debug(f"Registering external update callback for {listener_name} with {self.name} ({self.id_})")

        self.external_update_callback.append((callback, listener_name))

    def unregister_external_update_callback(self, callback: Callable, listener_name: str | None = None) -> None:
        """Unregister callback to be called when device state changes."""

        # Trace logging for @catellie
        # log.debug(f"Unregistering external update callback for {listener_name} with {self.name} ({self.id_})")

        self.external_update_callback.remove((callback, listener_name))

    async def async_handle_external_dual_state_change(self, state: BaseDevice.DeviceState | int | None) -> None:
        """Update device state when notified of externally-triggered change.

        Takes either a DeviceState or a DeviceState int value for the new state.
        """

        final_state = state.value if isinstance(state, Enum) else state

        await self.async_handle_external_attribute_change(
            {ATTR_STATE: final_state, ATTR_DESIRED_STATE: final_state},
            "WebSocket message",
        )

    async def async_handle_external_desired_state_change(self, state: BaseDevice.DeviceState | None) -> None:
        """Update device state when notified of externally-triggered change."""

        await self.async_handle_external_attribute_change(
            {ATTR_DESIRED_STATE: state.value if isinstance(state, Enum) else state},
            "WebSocket message",
        )

    # #
    # CASTING FUNCTIONS
    # #

    # Override CastingMixin functions to automatically pass in _raw_attribs dict.

    def _get_int(self, key: str) -> int | None:
        """Return int value from _raw_attributes."""
        return super()._safe_int_from_dict(self.raw_attributes, key)

    def _get_float(self, key: str) -> float | None:
        """Return float value from _raw_attributes."""
        return super()._safe_float_from_dict(self.raw_attributes, key)

    def _get_str(self, key: str) -> str | None:
        """Return str value from _raw_attributes."""
        return super()._safe_str_from_dict(self.raw_attributes, key)

    def _get_bool(self, key: str) -> bool | None:
        """Return bool value from _raw_attributes."""
        return super()._safe_bool_from_dict(self.raw_attributes, key)

    def _get_list(self, key: str, value_type: type) -> list | None:
        """Return list value from _raw_attributes."""
        return super()._safe_list_from_dict(self.raw_attributes, key, value_type)

    def _get_special(self, key: str, value_type: type) -> Any | None:
        """Return specified type value from _raw_attributes."""
        return super()._safe_special_from_dict(self.raw_attributes, key, value_type)

    # #
    # PLACEHOLDERS
    # #

    # All subclasses will have above functions. Only some will have the below and must be implemented as overloads.
    # Methods below are included here to silence mypy errors.

    @dataclass
    class DeviceAttributes:
        """Hold non-primary device state attributes. To be overridden by children."""

    class Command(Enum):
        """Hold device commands. To be overridden by children."""

    class DeviceState(Enum):
        """Hold device state values. To be overridden by children."""

    class Subtype(Enum):
        """Hold device subtypes. To be overridden by children."""

    def process_device_type_specific_data(self) -> None:
        """Process element specific data. To be overridden by children."""

        return

    async def async_change_setting(self, slug: str, new_value: Any) -> None:
        """Update specified configuration setting via extension."""

        if not self._config_change_callback:
            log.exception(
                "async_change_setting called for %s, which does not have a config_change_callback set.",
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
            "BaseDevice -> async_change_setting: Calling change setting function for %s %s (%s) via extension %s.",
            type(self).__name__,
            self.name,
            self.id_,
            extension,
        )

        updated_option = await self._config_change_callback(camera_name=self.name, slug=slug, new_value=new_value)

        self._settings["slug"] = updated_option
