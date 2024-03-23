"""Alarm.com controller for systems."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.adc.decorators import cli_action
from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.system import System

log = logging.getLogger(__name__)


class SystemController(BaseController[System]):
    """Controller for lights."""

    resource_type = ResourceType.SYSTEM
    _resource_class = System

    @cli_action()
    async def stop_alarms(self, id: str) -> None:
        """Stop all alarms and disarm a system."""

        await self._send_command(id, "stopAlarms")

    @cli_action()
    async def clear_smoke_sensor(self, system_id: str, smoke_sensor_id: str) -> None:
        """Change status of a smoke sensor to closed."""

        await self._send_command(system_id, "clearSmokeSensorStatus", {"data": smoke_sensor_id})

    @cli_action()
    async def clear_alarms_in_memory(self, system_id: str) -> None:
        """Clear alarms in memory on a system."""

        await self._send_command(system_id, "clearAlarmsInMemoryTrouble")
