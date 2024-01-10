"""Sensor websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.exceptions import UnsupportedDeviceType
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)

MOTION_EVENT_STATE_MAP = {
    EventType.Closed: Sensor.DeviceState.IDLE,
    EventType.OpenedClosed: Sensor.DeviceState.OPENED_CLOSED,
    EventType.Opened: Sensor.DeviceState.ACTIVE,
}
SENSOR_EVENT_STATE_MAP = {
    EventType.Closed: Sensor.DeviceState.CLOSED,
    EventType.OpenedClosed: Sensor.DeviceState.OPENED_CLOSED,
    EventType.Opened: Sensor.DeviceState.OPEN,
}


class SensorWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\sensors.ts

    SUPPORTED_DEVICE_TYPE = Sensor

    def get_state_from_event_type(self, message: EventMessage) -> Sensor.DeviceState:
        """Get sensor state from websocket message event type."""

        if type(message.device) != self.SUPPORTED_DEVICE_TYPE:
            raise UnsupportedDeviceType("Unexpected device type in message.")

        if not message.event_type:
            return Sensor.DeviceState.UNKNOWN

        match message.device.device_subtype:
            case Sensor.Subtype.MOTION_SENSOR:
                return MOTION_EVENT_STATE_MAP[message.event_type]
            case _:
                return SENSOR_EVENT_STATE_MAP[message.event_type]

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        if type(message.device) != Sensor:
            return

        match message:
            case EventMessage():
                match message.event_type:
                    case EventType.Closed | EventType.Opened | EventType.OpenedClosed:
                        await message.device.async_handle_external_state_change(
                            self.get_state_from_event_type(message)
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
