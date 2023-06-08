"""Light websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.light import Light
from pyalarmdotcomajax.websockets.const import EventType, PropertyChangeType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    PropertyChangeMessage,
    StatusChangeMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class LightWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = Light

    EVENT_STATE_MAP = {
        EventType.LightTurnedOff: Light.DeviceState.OFF,
        EventType.LightTurnedOn: Light.DeviceState.ON,
    }

    # Light messages use non-standard state values.
    STATE_MAP = {
        0: Light.DeviceState.OFF,
        1: Light.DeviceState.ON,
    }

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\lights.ts

        if type(message.device) != Light:
            return

        match message:
            case PropertyChangeMessage():
                match message.property:
                    case PropertyChangeType.LightColor:
                        # RGBW light not currently supported by library.
                        pass
            case StatusChangeMessage():
                await message.device.async_handle_external_dual_state_change(self.STATE_MAP[message.new_state])
            case EventMessage():
                match message.event_type:
                    case EventType.SwitchLevelChanged:
                        if message.value:
                            await message.device.async_handle_external_attribute_change(
                                {message.device.ATTRIB_LIGHT_LEVEL: int(message.value)}
                            )
                    case EventType.LightTurnedOff | EventType.LightTurnedOn:
                        await message.device.async_handle_external_dual_state_change(
                            self.EVENT_STATE_MAP[message.event_type]
                        )
                    case _:
                        log.debug(
                            f"Support for event {message.event_type} ({message.event_type_id}) not yet implemented"
                            f" by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                        )
            case _:
                log.debug(
                    f"Support for {type(message)} not yet implemented by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                )
