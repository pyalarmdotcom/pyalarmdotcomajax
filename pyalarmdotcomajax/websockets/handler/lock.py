"""Lock websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.lock import Lock
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    StatusChangeMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class LockWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = Lock

    EVENT_STATE_MAP = {
        EventType.DoorLocked: Lock.DeviceState.LOCKED,
        EventType.DoorUnlocked: Lock.DeviceState.UNLOCKED,
    }

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\locks.ts

        if type(message.device) != Lock:
            return

        match message:
            case StatusChangeMessage():
                if message.new_state:
                    await message.device.async_handle_external_state_change(int(message.new_state))
            case EventMessage():
                log.debug("Ignoring message. Already handled in separate status change message.")
            case _:
                log.debug(
                    f"Support for {type(message)} not yet implemented by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                )
