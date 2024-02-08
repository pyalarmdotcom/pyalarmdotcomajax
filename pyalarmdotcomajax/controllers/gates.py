"""Alarm.com controller for gates."""

from __future__ import annotations

import logging
from enum import StrEnum
from types import MappingProxyType

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.exceptions import UnsupportedOperation
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.gate import Gate, GateState
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import ResourceEventType

log = logging.getLogger(__name__)


class GateCommand(StrEnum):
    """Commands for ADC gates."""

    OPEN = "open"
    CLOSE = "close"


STATE_COMMAND_MAP = {
    GateState.OPEN: GateCommand.OPEN,
    GateState.CLOSED: GateCommand.CLOSE,
}


class GateController(BaseController[Gate]):
    """Controller for gates."""

    _resource_type = ResourceType.GATE
    _resource_class = Gate
    _resource_url = "{}web/api/devices/gates/{}"
    _event_state_map = MappingProxyType(
        {
            ResourceEventType.Opened: GateState.OPEN,
            ResourceEventType.Closed: GateState.CLOSED,
        }
    )
    _supported_resource_events = SupportedResourceEvents(events=[*_event_state_map.keys()])

    async def open(self, id: str) -> None:
        """Open gate."""

        await self.set_state(id, state=GateState.OPEN)

    async def close(self, id: str) -> None:
        """Close gate."""

        await self.set_state(id, state=GateState.CLOSED)

    async def set_state(self, id: str, state: GateState) -> None:
        """Change gate state."""

        if not (command := STATE_COMMAND_MAP.get(state)):
            raise UnsupportedOperation(f"State {state} not implemented.")

        await self._send_command(id, command)
