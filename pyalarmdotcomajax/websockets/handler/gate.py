"""Gate websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.gate import Gate
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    StatusChangeMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class GateWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = Gate

    EVENT_TO_STATE_MAP = {
        EventType.Opened: Gate.DeviceState.OPEN.value,
        EventType.Closed: Gate.DeviceState.CLOSED.value,
    }

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\gates.ts

        if type(message.device) != Gate:
            return

        match message:
            case StatusChangeMessage():
                if message.new_state:
                    await message.device.async_handle_external_state_change(message.new_state)

            case EventMessage():
                log.debug("Ignoring message. Already handled in separate status change message.")

            case _:
                log.debug(
                    f"Support for {type(message)} not yet implemented by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                )
