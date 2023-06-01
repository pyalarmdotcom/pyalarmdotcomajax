"""Sensor websocket message handler."""

from __future__ import annotations

import asyncio
import logging

from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class SensorWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\sensors.ts

    SUPPORTED_DEVICE_TYPE = Sensor

    async def async_get_state_from_event_type(self, message: EventMessage) -> int:
        """Get sensor state from websocket message event type."""

        match message.device.device_subtype:
            case Sensor.Subtype.MOTION_SENSOR:
                match message.event_type:
                    case EventType.Closed | EventType.OpenedClosed:
                        return Sensor.DeviceState.IDLE.value
                    case EventType.Opened:
                        return Sensor.DeviceState.ACTIVE.value
            case _:
                match message.event_type:
                    case EventType.Closed | EventType.OpenedClosed:
                        return Sensor.DeviceState.CLOSED.value
                    case EventType.Opened:
                        return Sensor.DeviceState.OPEN.value

        return Sensor.DeviceState.UNKNOWN.value

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        if type(message.device) != Sensor:
            return

        match message:
            case EventMessage():
                match message.event_type:
                    case EventType.Closed | EventType.Opened:
                        state = await self.async_get_state_from_event_type(message)
                        await message.device.async_handle_external_state_change(state)

                    case EventType.OpenedClosed:
                        # Lock ensures that state changes are executed in order.
                        lock = asyncio.Lock()

                        async with lock:
                            await message.device.async_handle_external_state_change(Sensor.DeviceState.OPEN.value)

                        async with lock:
                            await message.device.async_handle_external_state_change(
                                Sensor.DeviceState.CLOSED.value
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
