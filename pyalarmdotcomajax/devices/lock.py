"""Alarm.com lock."""
from __future__ import annotations

from enum import Enum
import logging

from . import BaseDevice
from . import DesiredStateMixin
from . import DeviceType

log = logging.getLogger(__name__)


class Lock(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com sensor element."""

    class DeviceState(Enum):
        """Enum of lock states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LockStatus.js

        UNKNOWN = 0
        LOCKED = 1
        UNLOCKED = 2

    class Command(Enum):
        """Commands for ADC locks."""

        LOCK = "lock"
        UNLOCK = "unlock"

    async def async_lock(self) -> None:
        """Send lock command."""

        await self._send_action_callback(
            device_type=DeviceType.LOCK,
            event=self.Command.LOCK,
            device_id=self.id_,
        )

    async def async_unlock(self) -> None:
        """Send unlock command."""

        await self._send_action_callback(
            device_type=DeviceType.LOCK,
            event=self.Command.UNLOCK,
            device_id=self.id_,
        )
