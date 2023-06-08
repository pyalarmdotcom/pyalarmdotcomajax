"""Partition websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.websockets.const import EventType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class PartitionWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = Partition

    EVENT_TO_STATE_MAP = {
        EventType.Disarmed: Partition.DeviceState.DISARMED,
        EventType.ArmedAway: Partition.DeviceState.ARMED_AWAY,
        EventType.ArmedStay: Partition.DeviceState.ARMED_STAY,
        EventType.ArmedNight: Partition.DeviceState.ARMED_NIGHT,
    }

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\partitions.ts

        if type(message.device) != Partition:
            return

        match message:
            case EventMessage():
                match message.event_type:
                    case EventType.Disarmed | EventType.ArmedAway | EventType.ArmedStay | EventType.ArmedNight:
                        await message.device.async_handle_external_dual_state_change(
                            self.EVENT_TO_STATE_MAP[message.event_type]
                        )
                    case EventType.Alarm | EventType.PolicePanic:
                        # TODO: Support these alarm events. These do not trigger a state change on ADC but rather trigger a notification.
                        log.debug(
                            f"Support for event {message.event_type} ({message.event_type_id}) not yet implemented"
                            f" by {self.SUPPORTED_DEVICE_TYPE.__name__}."
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
