"""Alarm.com thermostat."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from pyalarmdotcomajax.const import ATTR_STATE
from pyalarmdotcomajax.exceptions import UnexpectedResponse

from . import BaseDevice, DeviceType

log = logging.getLogger(__name__)


class Thermostat(BaseDevice):
    """Represent Alarm.com thermostat element."""

    # Fan duration of 0 is indefinite. otherwise value == hours.
    # TODO: desiredRts (remote temp sensor), desiredLocalDisplayLockingMode. Need user with remote sensors.
    # In identity info, check localizeTempUnitsToCelsius.

    ATTRIB_SETPOINT_OFFSET = "setpointOffset"
    ATTRIB_AMBIENT_TEMP = "ambientTemp"
    ATTRIB_FAN_MODE = "fanMode"
    ATTRIB_DESIRED_FAN_MODE = "desiredFanMode"
    ATTRIB_HEAT_SETPOINT = "heatSetpoint"
    ATTRIB_DESIRED_HEAT_SETPOINT = "desiredHeatSetpoint"
    ATTRIB_COOL_SETPOINT = "coolSetpoint"
    ATTRIB_DESIRED_COOL_SETPOINT = "desiredCoolSetpoint"

    class FanMode(Enum):
        """Enum of thermostat fan modes."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatFanMode.js

        AUTO = 0
        ON = 1

        # Not Used
        # AUTO_HIGH = 2
        # ON_HIGH = 3
        # AUTO_MEDIUM = 4
        # ON_MEDIUM = 5
        # CIRCULATE = 6
        # HUMIDITY = 7

    class DeviceState(BaseDevice.DeviceState):
        """Enum of thermostat states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatStatus.js

        UNKNOWN = 0
        OFF = 1
        HEAT = 2
        COOL = 3
        AUTO = 4
        AUX_HEAT = 5

    class LockMode(Enum):
        """Enum of thermostat lock modes."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatLock.js

        DISABLED = 0
        ENABLED = 1
        PARTIAL = 2

    class ScheduleMode(Enum):
        """Enum of thermostat programming modes."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatProgrammingMode.js

        MANUAL = 0
        SCHEDULED = 1
        SMART_SCHEDULES = 2

    class SetpointType(Enum):
        """Enum of thermostat setpoint types."""

        FIXED = 0
        AWAY = 1
        HOME = 2
        SLEEP = 3

    class Command(BaseDevice.Command):
        """Commands for ADC lights."""

        SET_STATE = "setState"

    @dataclass
    class ThermostatAttributes(BaseDevice.DeviceAttributes):
        """Thermostat attributes."""

        # Base
        temp_average: float | None  # Temperature from thermostat and all remote sensors, averaged.
        temp_at_tstat: float | None  # Temperature at thermostat only.
        setpoint_offset: float | None
        inferred_mode: (
            Thermostat.DeviceState | None
        )  # Indicates what thermostat is actually doing (cooling vs heating) if mode = auto.
        # Fan
        supports_fan_mode: bool | None
        supports_fan_indefinite: bool | None
        supports_fan_circulate_when_off: bool | None
        supported_fan_durations: list[int] | None
        fan_mode: Thermostat.FanMode | None
        # fan_duration: int | None # Fan duration is not updated in server response, even when fan is turned on for specific amount of time.
        # Temp
        supports_heat: bool | None
        supports_heat_aux: bool | None
        supports_cool: bool | None
        supports_auto: bool | None
        supports_setpoints: bool | None
        min_heat_setpoint: float | None
        max_heat_setpoint: float | None
        min_cool_setpoint: float | None
        max_cool_setpoint: float | None
        heat_setpoint: float | None
        cool_setpoint: float | None
        setpoint_buffer: float | None
        # Humidity
        supports_humidity: bool | None
        humidity: int | None
        # Schedules
        supports_schedules: bool | None
        supports_schedules_smart: bool | None
        schedule_mode: Thermostat.ScheduleMode | None

    @property
    def models(self) -> dict:
        """Return mapping of known ADC model IDs to manufacturer and model name. To be overridden by children."""
        return {
            4293: {"manufacturer": "Honeywell", "model": "T6 Pro"},
            10023: {"manufacturer": "ecobee", "model": "ecobee3 lite"},
        }

    @property
    def attributes(self) -> ThermostatAttributes:
        """Return thermostat attributes."""

        return self.ThermostatAttributes(
            temp_average=self._get_float("forwardingAmbientTemp"),
            temp_at_tstat=self._get_float(self.ATTRIB_AMBIENT_TEMP),
            inferred_mode=self._get_special("inferredMode", self.DeviceState),
            setpoint_offset=self._get_float(self.ATTRIB_SETPOINT_OFFSET),
            supports_fan_mode=self._get_bool("supportsFanMode"),
            supports_fan_indefinite=self._get_bool("supportsIndefiniteFanOn"),
            supports_fan_circulate_when_off=self._get_bool("supportsCirculateFanModeWhenOff"),
            supported_fan_durations=self._get_list("supportedFanDurations", int),
            fan_mode=self._get_special(self.ATTRIB_FAN_MODE, self.FanMode),
            supports_heat=self._get_bool("supportsHeatMode"),
            supports_heat_aux=self._get_bool("supportsAuxHeatMode"),
            supports_cool=self._get_bool("supportsCoolMode"),
            supports_auto=self._get_bool("supportsAutoMode"),
            supports_setpoints=self._get_bool("supportsSetpoints"),
            setpoint_buffer=self._get_float("autoSetpointBuffer"),
            min_heat_setpoint=self._get_float("minHeatSetpoint"),
            min_cool_setpoint=self._get_float("minCoolSetpoint"),
            max_heat_setpoint=self._get_float("maxHeatSetpoint"),
            max_cool_setpoint=self._get_float("maxCoolSetpoint"),
            heat_setpoint=self._get_float(self.ATTRIB_HEAT_SETPOINT),
            cool_setpoint=self._get_float(self.ATTRIB_COOL_SETPOINT),
            supports_humidity=self._get_bool("supportsHumidity"),
            humidity=self._get_int("humidityLevel"),
            supports_schedules=self._get_bool("supportsSchedules"),
            supports_schedules_smart=self._get_bool("supportsSmartSchedules"),
            schedule_mode=self._get_special("scheduleMode", self.ScheduleMode),
        )

    async def async_set_attribute(
        self,
        state: DeviceState | None = None,
        fan: tuple[FanMode, int] | None = None,  # int = duration
        cool_setpoint: float | None = None,
        heat_setpoint: float | None = None,
        schedule_mode: ScheduleMode | None = None,
    ) -> None:
        """Send command to HVAC unit."""

        msg_body: dict[str, float | int] = {}

        # Make sure we're only being asked to set one attribute at a time.
        if (attrib_list := [state, fan, cool_setpoint, heat_setpoint, schedule_mode]).count(None) < len(
            attrib_list
        ) - 1:
            raise UnexpectedResponse

        # Build the request body.
        if state:
            msg_body = {ATTR_STATE: state.value}
        elif fan:
            msg_body = {
                self.ATTRIB_DESIRED_FAN_MODE: self.FanMode(fan[0]).value,
                "desiredFanDuration": 0 if self.FanMode(fan[0]) == self.FanMode.AUTO else fan[1],
            }
        elif cool_setpoint:
            msg_body = {self.ATTRIB_DESIRED_COOL_SETPOINT: cool_setpoint}
        elif heat_setpoint:
            msg_body = {self.ATTRIB_DESIRED_HEAT_SETPOINT: heat_setpoint}
        elif schedule_mode:
            msg_body = {"desiredScheduleMode": schedule_mode.value}

        # Send
        await self._send_action(
            device_type=DeviceType.THERMOSTAT,
            event=self.Command.SET_STATE,
            device_id=self.id_,
            msg_body=msg_body,
        )
