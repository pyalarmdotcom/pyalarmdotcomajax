"""WaterSensor websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.water_sensor import WaterSensor
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    StatusChangeMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class WaterSensorWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = WaterSensor

    EVENT_TO_STATE_MAP = {
        EventType.Opened: WaterSensor.DeviceState.WET.value,
        EventType.Closed: WaterSensor.DeviceState.DRY.value,
    }

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\water_sensors.ts

        if type(message.device) != WaterSensor:
            return

        match message:
            case StatusChangeMessage():
                log.debug("Ignoring message. Already handled in separate status change message.")

            case EventMessage():
                match message.event_type:
                    case EventType.Opened | EventType.Closed:
                        await message.device.async_handle_external_state_change(
                            self.EVENT_TO_STATE_MAP[message.event_type]
                        )

            case _:
                log.debug(
                    f"Support for {type(message)} not yet implemented by {self.SUPPORTED_DEVICE_TYPE.__name__}."
                )
