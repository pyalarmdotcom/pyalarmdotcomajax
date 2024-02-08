"""Alarm.com controller for thermostats."""

from __future__ import annotations

import logging
from typing import Any

from pyalarmdotcomajax.const import ATTR_DESIRED_STATE, ATTR_STATE
from pyalarmdotcomajax.controllers.base import AdcResourceT, BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.thermostat import (
    TemperatureUnit,
    Thermostat,
    ThermostatFanMode,
    ThermostatScheduleMode,
    ThermostatState,
)
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import (
    BaseWSMessage,
    EventWSMessage,
    PropertyChangeWSMessage,
    ResourceEventType,
    ResourcePropertyChangeType,
)

log = logging.getLogger(__name__)

ATTR_FAN_MODE = "fanMode"
ATTR_SETPOINT_OFFSET = "setpointOffset"
ATTR_COOL_SETPOINT = "coolSetpoint"
ATTR_DESIRED_COOL_SETPOINT = "desiredCoolSetpoint"
ATTR_HEAT_SETPOINT = "heatSetpoint"
ATTR_DESIRED_HEAT_SETPOINT = "desiredHeatSetpoint"
ATTR_DESIRED_SCHEDULE_MODE = "desiredScheduleMode"


SUPPORTED_RESOURCE_EVENTS = SupportedResourceEvents(
    property_changes=[
        ResourcePropertyChangeType.CoolSetPoint,
        ResourcePropertyChangeType.HeatSetPoint,
        ResourcePropertyChangeType.AmbientTemperature,
    ],
    events=[
        ResourceEventType.ThermostatOffset,
        ResourceEventType.ThermostatModeChanged,
        ResourceEventType.ThermostatFanModeChanged,
        ResourceEventType.ThermostatSetPointChanged,
    ],
)


class ThermostatController(BaseController[Thermostat]):
    """Controller for thermostats."""

    _resource_type = ResourceType.THERMOSTAT
    _resource_class = Thermostat
    _resource_url = "{}web/api/devices/thermostats/{}"
    _supported_resource_events = SUPPORTED_RESOURCE_EVENTS

    async def set_state(
        self,
        id: str,
        state: ThermostatState | None = None,
        fan_mode: tuple[ThermostatFanMode, int] | None = None,
        cool_setpoint: float | None = None,
        heat_setpoint: float | None = None,
        schedule_mode: ThermostatScheduleMode | None = None,
        temperature_unit: TemperatureUnit | None = None,
    ) -> None:
        """Change thermostat state."""

        # Make sure that multiple attributes are not being set at the same time.
        if (attrib_list := [state, fan_mode, cool_setpoint, heat_setpoint, schedule_mode, temperature_unit]).count(
            None
        ) < len(attrib_list) - 1:
            raise ValueError("Only one attribute can be set at a time.")

        msg_body: dict[str, Any] = {}

        if state:
            msg_body[ATTR_STATE] = state.value
        elif fan_mode:
            msg_body["desiredFanMode"] = fan_mode[0].value
            msg_body["desiredFanDuration"] = 0 if fan_mode[0] == ThermostatFanMode.AUTO else fan_mode[1]
        elif cool_setpoint:
            msg_body[ATTR_DESIRED_COOL_SETPOINT] = cool_setpoint
        elif heat_setpoint:
            msg_body[ATTR_DESIRED_HEAT_SETPOINT] = heat_setpoint
        elif schedule_mode:
            msg_body[ATTR_DESIRED_SCHEDULE_MODE] = schedule_mode.value

        await self._send_command(id, "setState", msg_body)

    async def _handle_event(self, adc_resource: AdcResourceT, message: BaseWSMessage) -> AdcResourceT:
        """Handle light-specific WebSocket events."""

        updated_data: dict[str, Any] = {}

        if isinstance(message, EventWSMessage) and message.value:
            if message.subtype == ResourceEventType.ThermostatModeChanged:
                updated_data[ATTR_STATE] = int(message.value) + 1
                updated_data[ATTR_DESIRED_STATE] = int(message.value) + 1

            elif message.subtype == ResourceEventType.ThermostatFanModeChanged:
                updated_data[ATTR_FAN_MODE] = int(message.value)

            elif message.subtype == ResourceEventType.ThermostatOffset:
                updated_data[ATTR_SETPOINT_OFFSET] = message.value

        if isinstance(message, PropertyChangeWSMessage) and message.value:
            adjusted_value = message.value / 100

            if self._bridge.auth_controller.use_celsius:
                adjusted_value = round(((adjusted_value - 32) * 5 / 9), 1)

            if message.subtype == ResourcePropertyChangeType.CoolSetPoint:
                updated_data[ATTR_COOL_SETPOINT] = adjusted_value
                updated_data[ATTR_DESIRED_COOL_SETPOINT] = adjusted_value

            elif message.subtype == ResourcePropertyChangeType.HeatSetPoint:
                updated_data[ATTR_HEAT_SETPOINT] = adjusted_value
                updated_data[ATTR_DESIRED_HEAT_SETPOINT] = adjusted_value

        adc_resource.api_resource.attributes.update(updated_data)

        return adc_resource
