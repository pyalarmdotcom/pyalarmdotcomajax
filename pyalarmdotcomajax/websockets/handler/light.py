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

    STATE_MAP = {
        0: Light.DeviceState.OFF.value,
        1: Light.DeviceState.ON.value,
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
                if message.new_state in self.STATE_MAP:
                    await message.device.async_handle_external_state_change(self.STATE_MAP[message.new_state])
                else:
                    log.exception(
                        f"{self.__class__.__name__}: Failed to update"
                        f" {message.device.name} ({message.device.id_}). Unknown state: {message.new_state}."
                    )
            case EventMessage():
                match message.event_type:
                    case EventType.SwitchLevelChanged:
                        if message.value:
                            await message.device.async_handle_external_attribute_change(
                                {message.device.ATTRIB_LIGHT_LEVEL: int(message.value)}
                            )
                            await message.device.async_log_new_attribute("brightness", message.device.brightness)
                    case EventType.LightTurnedOff | EventType.LightTurnedOn:
                        log.debug("Ignoring message. Already handled in separate status change message.")
                    case _:
                        log.debug(
                            f"Support for event {message.event_type} ({message.event_type_id}) not yet implemented"
                            f" by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                        )
            case _:
                log.debug(
                    f"Support for {type(message)} not yet implemented by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                )
