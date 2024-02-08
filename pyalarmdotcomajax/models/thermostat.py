"""Alarm.com model for thermostats."""

from abc import ABC
from dataclasses import dataclass, field
from enum import IntEnum

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    BaseManagedDeviceAttributes,
    DeviceState,
    ResourceType,
)


@dataclass
class TemperatureDeviceAttributes(BaseManagedDeviceAttributes[DeviceState], ABC):
    """Attributes of temperature device."""

    # fmt: off
    ambient_temp: float = field(metadata={"description": "The current temperature reported by the device."})
    has_rts_issue: bool = field(metadata={"description": "Does this device have a Rts issue?"})
    humidity_level: int = field(metadata={"description": "The current humidity level reported by the device."})
    is_paired: bool = field(metadata={"description": "Is this device paired to another?"})
    supports_humidity: bool = field(metadata={"description": "Whether the device supports humidity."})

    # supports_pairing: bool  # Does this device support pairing? Does a thermostat support pairing to temperature sensors or does a temperature sensor support pairing to thermostats?
    # temp_forwarding_active: bool  # Is this device's temperature currently being used to drive itself or another device?
    # fmt: on


class ThermostatState(IntEnum):
    """Thermostat states."""

    UNKNOWN = 0
    OFF = 1
    HEAT = 2
    COOL = 3
    AUTO = 4
    AUXHEAT = 5


class ThermostatReportedFanMode(IntEnum):
    """Thermostat fan modes as reported in the thermostat response object."""

    AUTO_LOW = 0
    ON_LOW = 1
    AUTO_HIGH = 2
    ON_HIGH = 3
    AUTO_MEDIUM = 4
    ON_MEDIUM = 5
    CIRCULATE = 6
    HUMIDITY = 7


class ThermostatFanMode(IntEnum):
    """User-facomg thermostat fan modes."""

    UNKNOWN = -1
    AUTO = 0
    ON = 1
    CIRCULATE = 2


class ThermostatScheduleMode(IntEnum):
    """Thermostat schedule modes."""

    MANUAL_MODE = 0
    SCHEDULED = 1
    SMART_SCHEDULES = 2


class TemperatureUnit(IntEnum):
    """Temperature units."""

    FAHRENHEIT = 1
    CELSIUS = 2
    KELVIN = 3


THERMOSTAT_MODELS = {
    4293: {"manufacturer": "Honeywell", "model": "T6 Pro"},
    10023: {"manufacturer": "ecobee", "model": "ecobee3 lite"},
}


@dataclass
class ThermostatAttributes(TemperatureDeviceAttributes[ThermostatState]):
    """Attributes of temperature device."""

    # fmt: off
    auto_setpoint_buffer: float = field(metadata={"description": "The minimum buffer between the heat and cool setpoints."})
    away_cool_setpoint: float = field(metadata={"description": "The away preset cool setpoint."})
    away_heat_setpoint: float = field(metadata={"description": "The away preset heat setpoint."})
    cool_setpoint: float = field(metadata={"description": "The current cool setpoint."})
    desired_cool_setpoint: float = field(metadata={"description": "The desired cool setpoint."})
    desired_fan_mode: ThermostatReportedFanMode = field(metadata={"description": "The desired fan mode."})
    desired_heat_setpoint: float = field(metadata={"description": "The desired heat setpoint."})
    fan_duration: int | None = field(metadata={"description": "The duration to run the fan. Only used to offset the commands. Fan duration is not updated in server response, even when fan is turned on for specific amount of time."})
    fan_mode: ThermostatReportedFanMode = field(metadata={"description": "The current fan mode."})
    forwarding_ambient_temp: float = field(metadata={"description": "The current temperature including any additional temperature sensor averaging."})
    has_pending_setpoint_change: bool = field(metadata={"description": "Does the thermostat have a pending setpoint change?"})
    has_pending_temp_mode_change: bool = field(metadata={"description": "Does the thermostat have a pending temp mode change?"})
    heat_setpoint: float = field(metadata={"description": "The current heat setpoint."})
    inferred_state: str = field(metadata={"description": "The mode we think the thermostat is using when in auto mode (auto heat or auto cool)"})
    is_controlled: bool = field(metadata={"description": "Whether the thermostat is controlled by another thermostat."})
    is_pool_controller: bool = field(metadata={"description": "Whether the thermostat is a pool controller."})
    max_aux_heat_setpoint: float = field(metadata={"description": "The max valid aux heat setpoint."})
    max_cool_setpoint: float = field(metadata={"description": "The max valid cool setpoint."})
    max_heat_setpoint: float = field(metadata={"description": "The max valid heat setpoint."})
    min_aux_heat_setpoint: float = field(metadata={"description": "The min valid aux heat setpoint."})
    min_cool_setpoint: float = field(metadata={"description": "The min valid cool setpoint."})
    min_heat_setpoint: float = field(metadata={"description": "The min valid heat setpoint."})
    requires_setup: bool = field(metadata={"description": "Does the thermostat require a setup wizard to be run before being used?"})
    schedule_mode: str = field(metadata={"description": "The schedule mode."})
    setpoint_offset: float = field(metadata={"description": "The amount to increment or decrement the setpoint by when changing it."})
    supported_fan_durations: list[int] = field(metadata={"description": "The fan mode durations that the thermostat supports"})
    supports_auto_mode: bool = field(metadata={"description": "Whether the thermostat supports the auto temp mode."})
    supports_aux_heat_mode: bool = field(metadata={"description": "Whether the thermostat supports the aux heat temp mode."})
    supports_circulate_fan_mode_always: bool = field(metadata={"description": "Whether the thermostat supports the circulate fan mode regardless of temp mode."})
    supports_circulate_fan_mode_when_off: bool = field(metadata={"description": "Whether the thermostat supports the circulate fan mode when in OFF mode."})
    supports_cool_mode: bool = field(metadata={"description": "Whether the thermostat supports the cool temp mode."})
    supports_fan_mode: bool = field(metadata={"description": "Whether the thermostat supports fan mode control."})
    supports_heat_mode: bool = field(metadata={"description": "Whether the thermostat supports the heat temp mode."})
    supports_indefinite_fan_on: bool = field(metadata={"description": "Whether the thermostat supports running the fan indefinitely."})
    supports_off_mode: bool = field(metadata={"description": "Whether the thermostat supports the off temp mode."})
    supports_schedules: bool = field(metadata={"description": "Whether the thermostat supports schedules."})
    supports_setpoints: bool = field(metadata={"description": "Whether the thermostat supports setpoints."})

    # active_sensors: List[str]  # The collection of sensors (including the thermostat) that are currently driving the HVAC system.
    # boiler_control_system: str  # The boiler control system this device belongs to.
    # controlled_thermostats: List[str]  # The thermostats that this thermostat controls
    # cool_rts_presets: List[float]  # The paired RTS devices on cool mode, separated by setpoint.
    # desired_local_display_locking_mode: str  # The desired local display locking mode.
    # has_rts_issue: bool  # Indicates an issue with RTS forwarding.
    # heat_rts_presets: List[float]  # The paired RTS devices on heat mode, separated by setpoint.
    # home_cool_setpoint: float  # The home preset cool setpoint.
    # home_heat_setpoint: float  # The home preset heat setpoint.
    # local_display_locking_mode: str  # The current local display locking mode.
    # peak_protect: bool  # The Peak Protect
    # pending_state_changes: List[str]  # Property that contains state changes to be committed
    # remote_temperature_sensors: List[str]  # The remote temperature sensors associated with the thermostat.
    # rule_suggestions: List[str]  # An array of rule alerts for this thermostat.
    # schedule_icon_name: str  # The name for the schedule icon.
    # sleep_cool_setpoint: float  # The sleep preset cool setpoint.
    # sleep_heat_setpoint: float  # The sleep preset heat setpoint.
    # supports_hvac_analytics: bool  # Whether the thermostat supports HVAC Analytics.
    # supports_local_display_locking: bool  # Whether the thermostat supports local display locking.
    # supports_partial_local_display_locking: bool  # Whether the thermostat supports partial local display locking.
    # supports_smart_schedules: bool  # Whether the thermostat supports the Smart Schedule mode.
    # supports_third_party_settings: bool  # Whether the thermostat supports third party settings.
    # thermostat_settings_template: str  # The thermostat settings template applied to this thermostat.
    # third_party_settings_url: str  # The URL for third party settings.
    # third_party_settings_url_desc: str  # The description for third party settings URL.
    # valve_switches: List[str]  # The valve switches associated with the thermostat.
    # fmt: on

    @property
    def has_dirty_setpoint(self) -> bool:
        """Whether the thermostat has a setpoint that is currently being changed."""

        return self.has_pending_setpoint_change or self.has_pending_temp_mode_change


@dataclass
class Thermostat(AdcDeviceResource[ThermostatAttributes]):
    """Thermostat resource."""

    # Fan duration of 0 is indefinite. otherwise value == hours.

    resource_type = ResourceType.THERMOSTAT
    attributes_type = ThermostatAttributes
    resource_models = THERMOSTAT_MODELS

    @property
    def fan_mode(self) -> ThermostatFanMode:
        """The current fan mode."""

        if self.attributes.desired_fan_mode in (
            ThermostatReportedFanMode.AUTO_LOW,
            ThermostatReportedFanMode.AUTO_MEDIUM,
        ):
            return ThermostatFanMode.AUTO
        if self.attributes.desired_fan_mode in (
            ThermostatReportedFanMode.ON_LOW,
            ThermostatReportedFanMode.ON_MEDIUM,
            ThermostatReportedFanMode.ON_HIGH,
        ):
            return ThermostatFanMode.ON
        if self.attributes.desired_fan_mode == ThermostatReportedFanMode.CIRCULATE:
            return ThermostatFanMode.CIRCULATE
        return ThermostatFanMode.UNKNOWN
