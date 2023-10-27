"""Alarm.com scene."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import BaseDevice, DeviceType

log = logging.getLogger(__name__)


class Scene(BaseDevice):
    """Represent Alarm.com scene element."""

    def __init__(
        self,
        id_: str,
        raw_device_data: dict,
        send_action_callback: Callable,
        **kwargs: Any,
    ) -> None:
        """Initialize base element class."""

        super().__init__(
            id_=id_, raw_device_data=raw_device_data, send_action_callback=send_action_callback, **kwargs
        )

    @dataclass
    class SceneAttributes(BaseDevice.DeviceAttributes):
        """Scene attributes."""

        disarms_alarm: bool | None  # Specifies whether the scene disarms the alarm.

    @property
    def read_only(self) -> bool | None:
        """Return whether logged in user has permission to change state."""
        return not can_be_executed if (can_be_executed := self._get_bool("canBeExecuted")) is not None else None

    class Command(BaseDevice.Command):
        """Commands for ADC scenes."""

        EXECUTE = "execute"

    @property
    def name(self) -> str:
        """Return user-assigned device name."""

        return str(self.raw_attributes["name"])

    @property
    def attributes(self) -> SceneAttributes | None:
        """Return thermostat attributes."""

        return self.SceneAttributes(disarms_alarm=self._get_bool("hasDisarmAction"))

    async def execute(self) -> None:
        """Send execute command."""

        await self._send_action(
            device_type=DeviceType.SCENE,
            event=self.Command.EXECUTE,
            device_id=self.id_,
        )
