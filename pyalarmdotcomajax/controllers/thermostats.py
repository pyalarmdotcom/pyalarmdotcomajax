"""Alarm.com controller for thermostats."""

# ruff: noqa: UP007

# from __future__ import annotations

import logging
from typing import Annotated, Any, Optional

import typer

from pyalarmdotcomajax.adc.util import ValueEnum, cli_action
from pyalarmdotcomajax.const import ATTR_DESIRED_STATE, ATTR_STATE
from pyalarmdotcomajax.controllers.base import AdcResourceT, BaseController
from pyalarmdotcomajax.models.auth import OtpType
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.thermostat import (
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

    resource_type = ResourceType.THERMOSTAT
    _resource_class = Thermostat
    _supported_resource_events = SUPPORTED_RESOURCE_EVENTS

    @cli_action()
    async def set_state(
        self,
        id: Annotated[str, typer.Option(help="The ID of the thermostat.", show_default=False)],
        state: Annotated[
            Optional[OtpType],
            typer.Option(
                click_type=ValueEnum(ThermostatState, "UNKNOWN"),
                case_sensitive=False,
                show_default=False,
                help="The desired state of the thermostat.",
            ),
        ] = None,
        fan_mode: Annotated[
            Optional[ThermostatFanMode],
            typer.Option(
                click_type=ValueEnum(ThermostatFanMode, ["UNKNOWN"]),
                case_sensitive=False,
                show_default=False,
                help="The desired fan mode.",
            ),
        ] = None,
        fan_mode_duration: Annotated[
            Optional[int],
            typer.Option(help="The duration for which the desired fan mode should run.", show_default=False),
        ] = None,
        cool_setpoint: Annotated[
            Optional[float], typer.Option(help="The desired cool setpoint.", show_default=False)
        ] = None,
        heat_setpoint: Annotated[
            Optional[float], typer.Option(help="The desired heat setpoint.", show_default=False)
        ] = None,
        schedule_mode: Annotated[
            Optional[ThermostatScheduleMode],
            typer.Option(
                click_type=ValueEnum(ThermostatScheduleMode),
                case_sensitive=False,
                show_default=False,
                help="The desired schedule mode.",
            ),
        ] = None,
    ) -> None:
        """
        Set thermostat attributes.

        Only one attribute can be set at a time, with the exception of --fan-mode and --fan-mode-duration, which must be set together.
        """
        # Make sure that multiple attributes are not being set at the same time.
        if [fan_mode, fan_mode_duration].count(None) == 1:
            raise ValueError("Fan_mode and fan_mode_duration must be used together.")
        if (
            attrib_list := [state, fan_mode, fan_mode_duration, cool_setpoint, heat_setpoint, schedule_mode]
        ).count(None) < len(attrib_list) - 1:
            raise ValueError("Only one attribute can be set at a time.")

        msg_body: dict[str, Any] = {}

        if state:
            msg_body[ATTR_STATE] = state.value
        elif fan_mode:
            msg_body["desiredFanMode"] = fan_mode.value
            msg_body["desiredFanDuration"] = 0 if fan_mode == ThermostatFanMode.AUTO else fan_mode_duration
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
