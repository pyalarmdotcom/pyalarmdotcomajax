"""Alarm.com controller for lights."""

# from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Annotated, Any

import typer

from pyalarmdotcomajax.adc.decorators import cli_action
from pyalarmdotcomajax.adc.params import Param_Id
from pyalarmdotcomajax.const import ATTR_DESIRED_STATE, ATTR_STATE
from pyalarmdotcomajax.controllers.base import AdcResourceT, BaseController
from pyalarmdotcomajax.exceptions import UnsupportedOperation
from pyalarmdotcomajax.models.base import ResourceType, StrEnum
from pyalarmdotcomajax.models.light import Light, LightState
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import (
    BaseWSMessage,
    EventWSMessage,
    ResourceEventType,
    ResourcePropertyChangeType,
)

log = logging.getLogger(__name__)

ATTR_LIGHT_LEVEL = "lightLevel"


class LightCommand(StrEnum):
    """Light commands."""

    ON = "turnOn"
    OFF = "turnOff"


STATE_COMMAND_MAP = {
    LightState.ON: LightCommand.ON,
    LightState.OFF: LightCommand.OFF,
}


class LightController(BaseController[Light]):
    """Controller for lights."""

    resource_type = ResourceType.LIGHT
    _resource_class = Light
    _event_state_map = MappingProxyType(
        {
            ResourceEventType.LightTurnedOff: LightState.OFF,
            ResourceEventType.LightTurnedOn: LightState.ON,
        }
    )
    _supported_resource_events = SupportedResourceEvents(
        property_changes=[ResourcePropertyChangeType.LightColor],
        events=[ResourceEventType.SwitchLevelChanged, *_event_state_map.keys()],
    )

    @cli_action()
    async def turn_on(self, id: Param_Id) -> None:
        """Turn on a light."""

        await self.set_state(id, state=LightState.ON)

    @cli_action()
    async def turn_off(self, id: Param_Id) -> None:
        """Turn off a light."""

        await self.set_state(id, state=LightState.OFF)

    @cli_action()
    async def set_brightness(
        self,
        id: Param_Id,
        brightness: Annotated[
            int,
            typer.Argument(
                help="A dimmable light's brightness. (Range: 0-100)",
                max=100,
                min=0,
                show_default=False,
            ),
        ],
    ) -> None:
        """Turn on a light and set its brightness."""

        await self.set_state(id, state=LightState.ON, brightness=brightness)

    async def set_state(self, id: str, state: LightState, brightness: int | None = None) -> None:
        """Change light state."""

        msg_body: dict[str, Any] = {}

        if state == LightState.ON:
            command = LightCommand.ON
        elif state == LightState.OFF:
            command = LightCommand.OFF
        else:
            raise UnsupportedOperation(f"Light state {state} not implemented.")

        if brightness:
            if not self[id].attributes.is_dimmer:
                raise UnsupportedOperation("Light does not support brightness.")
            msg_body["dimmerLevel"] = brightness

        await self._send_command(id, command.value, msg_body)

    async def _handle_event(self, adc_resource: AdcResourceT, message: BaseWSMessage) -> AdcResourceT:
        """Handle light-specific WebSocket events."""

        if (
            isinstance(message, EventWSMessage)
            and message.subtype == ResourceEventType.SwitchLevelChanged
            and message.value
        ):
            # Set state based on light level
            state = LightState.ON if int(message.value) > 0 else LightState.OFF

            adc_resource.api_resource.attributes.update(
                {
                    ATTR_LIGHT_LEVEL: int(message.value),
                    ATTR_STATE: state.value,
                    ATTR_DESIRED_STATE: state.value,
                }
            )

        return adc_resource
