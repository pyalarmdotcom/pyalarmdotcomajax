"""WaterValve websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.water_valve import WaterValve
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    StatusChangeMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)

EVENT_STATE_MAP = {
    EventType.Opened: WaterValve.DeviceState.OPEN,
    EventType.Closed: WaterValve.DeviceState.CLOSED,
}


class WaterValveWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = WaterValve

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # https://www.alarm.com/web/system/assets/customer-site/websockets/handlers/water-valves.js

        if type(message.device) != WaterValve:
            return

        match message:
            case StatusChangeMessage():
                if message.new_state:
                    await message.device.async_handle_external_dual_state_change(message.new_state)

            case EventMessage():
                match message.event_type:
                    case EventType.Opened | EventType.Closed:
                        await message.device.async_handle_external_dual_state_change(
                            EVENT_STATE_MAP[message.event_type]
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
