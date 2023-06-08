"""Alarm.com light."""
from __future__ import annotations

import logging

from pyalarmdotcomajax.devices import BaseDevice, DeviceType

log = logging.getLogger(__name__)


# WebSocket Handler: https://www.alarm.com/web/system/assets/customer-ember/websockets/handlers/lights.ts
class Light(BaseDevice):
    """Represent Alarm.com light element."""

    ATTRIB_LIGHT_LEVEL = "lightLevel"

    class DeviceState(BaseDevice.DeviceState):
        """Enum of light states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LightStatus.js

        OFFLINE = 0
        NOSTATE = 1
        ON = 2
        OFF = 3
        LEVELCHANGE = 4

    class Command(BaseDevice.Command):
        """Commands for ADC lights."""

        ON = "turnOn"
        OFF = "turnOff"

    @property
    def brightness(self) -> int | None:
        """Return light's brightness."""
        if not self.raw_attributes.get("isDimmer", False):
            return None

        if isinstance(level := self.raw_attributes.get(self.ATTRIB_LIGHT_LEVEL, 0), int):
            return level

        return None

    @property
    def supports_state_tracking(self) -> bool | None:
        """Return whether the light reports its current state."""

        if isinstance(supports := self.raw_attributes.get("stateTrackingEnabled"), bool):
            return supports

        return None

    async def async_turn_on(self, brightness: int | None = None) -> None:
        """Send turn on command with optional brightness."""

        msg_body: dict = {}
        if brightness:
            msg_body["dimmerLevel"] = brightness

        await self._send_action(
            device_type=DeviceType.LIGHT,
            event=self.Command.ON,
            device_id=self.id_,
            msg_body=msg_body,
        )

    async def async_turn_off(self) -> None:
        """Send turn off command."""

        await self._send_action(
            device_type=DeviceType.LIGHT,
            event=self.Command.OFF,
            device_id=self.id_,
        )
