"""Thermostat websocket message handler."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices.thermostat import Thermostat
from pyalarmdotcomajax.websockets.const import EventType, PropertyChangeType
from pyalarmdotcomajax.websockets.handler import BaseWebSocketHandler
from pyalarmdotcomajax.websockets.messages import (
    EventMessage,
    PropertyChangeMessage,
    WebSocketMessage,
)

log = logging.getLogger(__name__)


class ThermostatWebSocketHandler(BaseWebSocketHandler):
    """Base class for device-type-specific websocket message handler."""

    SUPPORTED_DEVICE_TYPE = Thermostat

    async def process_message(self, message: WebSocketMessage) -> None:
        """Handle websocket message."""

        # www.alarm.com\web\system\assets\customer-ember\websockets\handlers\thermostats.ts

        if (
            type(message.device) != Thermostat
            or not message.device
            or not (hasattr(message, "value") and isinstance(message.value, int | float))
        ):
            return

        match message:
            case PropertyChangeMessage():
                match message.property:
                    case PropertyChangeType.CoolSetPoint | PropertyChangeType.HeatSetPoint:
                        await message.device.async_handle_external_attribute_change(
                            {
                                (
                                    message.device.ATTRIB_HEAT_SETPOINT
                                    if message.property == PropertyChangeType.HeatSetPoint
                                    else message.device.ATTRIB_COOL_SETPOINT
                                ): (message.value / 100),
                                (
                                    message.device.ATTRIB_DESIRED_HEAT_SETPOINT
                                    if message.property == PropertyChangeType.HeatSetPoint
                                    else message.device.ATTRIB_DESIRED_COOL_SETPOINT
                                ): (message.value / 100),
                            },
                        )

                    case PropertyChangeType.AmbientTemperature:
                        await message.device.async_handle_external_attribute_change(
                            {message.device.ATTRIB_AMBIENT_TEMP: message.value / 100},
                        )

            case EventMessage():
                match message.event_type:
                    case EventType.ThermostatOffset:
                        await message.device.async_handle_external_attribute_change(
                            {message.device.ATTRIB_SETPOINT_OFFSET: message.value},
                        )

                    case EventType.ThermostatModeChanged:
                        await message.device.async_handle_external_dual_state_change(
                            message.device.DeviceState(message.value + 1)
                        )

                    case EventType.ThermostatFanModeChanged:
                        await message.device.async_handle_external_attribute_change(
                            {
                                message.device.ATTRIB_FAN_MODE: message.value,
                                message.device.ATTRIB_DESIRED_FAN_MODE: message.value,
                            },
                        )

                    case EventType.ThermostatSetPointChanged:
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
