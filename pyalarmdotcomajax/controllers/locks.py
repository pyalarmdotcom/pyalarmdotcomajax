"""Alarm.com controller for locks."""

from __future__ import annotations

import logging
from enum import StrEnum
from types import MappingProxyType

from pyalarmdotcomajax.adc.util import Param_Id, cli_action
from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.exceptions import UnsupportedOperation
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.lock import Lock, LockState
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import ResourceEventType

log = logging.getLogger(__name__)


class LockCommand(StrEnum):
    """Commands for ADC locks."""

    LOCK = "lock"
    UNLOCK = "unlock"


STATE_COMMAND_MAP = {
    LockState.LOCKED: LockCommand.LOCK,
    LockState.UNLOCKED: LockCommand.UNLOCK,
}


class LockController(BaseController[Lock]):
    """Controller for locks."""

    resource_type = ResourceType.LOCK
    _resource_class = Lock
    _event_state_map = MappingProxyType(
        {
            ResourceEventType.DoorLocked: LockState.LOCKED,
            ResourceEventType.DoorUnlocked: LockState.UNLOCKED,
        }
    )
    _supported_resource_events = SupportedResourceEvents(events=[*_event_state_map.keys()])

    @cli_action()
    async def lock(self, id: Param_Id) -> None:
        """Lock a lock."""

        await self.set_state(id, state=LockState.LOCKED)

    @cli_action()
    async def unlock(self, id: Param_Id) -> None:
        """Unlock a lock."""

        await self.set_state(id, state=LockState.UNLOCKED)

    async def set_state(self, id: str, state: LockState) -> None:
        """Change lock state."""

        if not (command := STATE_COMMAND_MAP.get(state)):
            raise UnsupportedOperation(f"State {state} not implemented.")

        await self._send_command(id, command.value)
