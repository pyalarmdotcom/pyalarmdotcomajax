"""Alarm.com garage door."""
from __future__ import annotations

import logging
from enum import Enum

from pyalarmdotcomajax.devices import DeviceType

from . import BaseDevice

log = logging.getLogger(__name__)


class GarageDoor(BaseDevice):
    """Represent Alarm.com garage door element."""

    class DeviceState(Enum):
        """Enum of garage door states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/GarageDoorStatus.js

        UNKNOWN = 0
        OPEN = 1
        CLOSED = 2

    class Command(Enum):
        """Commands for ADC garage doors."""

        OPEN = "open"
        CLOSE = "close"

    async def async_open(self) -> None:
        """Send open command."""

        await self._send_action_callback(
            device_type=DeviceType.GARAGE_DOOR,
            event=self.Command.OPEN,
            device_id=self.id_,
        )

    async def async_close(self) -> None:
        """Send close command."""

        await self._send_action_callback(
            device_type=DeviceType.GARAGE_DOOR,
            event=self.Command.CLOSE,
            device_id=self.id_,
        )
