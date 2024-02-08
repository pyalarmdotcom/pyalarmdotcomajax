"""Alarm.com controller for garage doors."""

from __future__ import annotations

import logging
from types import MappingProxyType

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.exceptions import UnsupportedOperation
from pyalarmdotcomajax.models.base import ResourceType, StrEnum
from pyalarmdotcomajax.models.garage_door import GarageDoor, GarageDoorState
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import ResourceEventType

log = logging.getLogger(__name__)


class GarageDoorCommand(StrEnum):
    """Commands for ADC garage doors."""

    OPEN = "open"
    CLOSE = "close"


STATE_COMMAND_MAP = {
    GarageDoorState.OPEN: GarageDoorCommand.OPEN,
    GarageDoorState.CLOSED: GarageDoorCommand.CLOSE,
}


class GarageDoorController(BaseController[GarageDoor]):
    """Controller for garage doors."""

    _resource_type = ResourceType.GARAGE_DOOR
    _resource_class = GarageDoor
    _resource_url = "{}web/api/devices/garageDoors/{}"
    _event_state_map = MappingProxyType(
        {
            ResourceEventType.Opened: GarageDoorState.OPEN,
            ResourceEventType.Closed: GarageDoorState.CLOSED,
        }
    )
    _supported_resource_events = SupportedResourceEvents(events=[*_event_state_map.keys()])

    async def open(self, id: str) -> None:
        """Open garage door."""

        await self.set_state(id, state=GarageDoorState.OPEN)

    async def close(self, id: str) -> None:
        """Close garage door."""

        await self.set_state(id, state=GarageDoorState.CLOSED)

    async def set_state(self, id: str, state: GarageDoorState) -> None:
        """Change garage door state."""

        if not (command := STATE_COMMAND_MAP.get(state)):
            raise UnsupportedOperation(f"State {state} not implemented.")

        await self._send_command(id, command)
