"""Alarm.com lock."""
from __future__ import annotations

import logging

from pyalarmdotcomajax.devices import DeviceType

from . import BaseDevice

log = logging.getLogger(__name__)


class Lock(BaseDevice):
    """Represent Alarm.com sensor element."""

    class DeviceState(BaseDevice.DeviceState):
        """Enum of lock states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LockStatus.js

        UNKNOWN = 0
        LOCKED = 1
        UNLOCKED = 2

    class Command(BaseDevice.Command):
        """Commands for ADC locks."""

        LOCK = "lock"
        UNLOCK = "unlock"

    async def async_lock(self) -> None:
        """Send lock command."""

        await self.async_handle_external_desired_state_change(self.DeviceState.LOCKED)

        await self._send_action(
            device_type=DeviceType.LOCK,
            event=self.Command.LOCK,
            device_id=self.id_,
        )

    async def async_unlock(self) -> None:
        """Send unlock command."""

        await self.async_handle_external_desired_state_change(self.DeviceState.UNLOCKED)

        await self._send_action(
            device_type=DeviceType.LOCK,
            event=self.Command.UNLOCK,
            device_id=self.id_,
        )
