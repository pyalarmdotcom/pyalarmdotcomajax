"""Alarm.com gate."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging

from . import BaseDevice, DesiredStateMixin, DeviceType

log = logging.getLogger(__name__)


class Gate(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com gate element."""

    @dataclass
    class GateAttributes(BaseDevice.DeviceAttributes):
        """Gate attributes."""

        supports_remote_close: bool | None  # Specifies whether the gate can be closed remotely.

    class DeviceState(Enum):
        """Enum of gate states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/GateStatus.js

        UNKNOWN = 0
        OPEN = 1
        CLOSED = 2

    class Command(Enum):
        """Commands for ADC gates."""

        OPEN = "open"
        CLOSE = "close"

    @property
    def attributes(self) -> GateAttributes | None:
        """Return thermostat attributes."""

        return self.GateAttributes(
            supports_remote_close=self._get_bool("supportsRemoteClose"),
        )

    async def async_open(self) -> None:
        """Send open command."""

        await self._send_action_callback(
            device_type=DeviceType.GATE,
            event=self.Command.OPEN,
            device_id=self.id_,
        )

    async def async_close(self) -> None:
        """Send close command."""

        if (
            self.attributes is not None
            and hasattr(self.attributes, "supports_remote_close")
            and not self.attributes.supports_remote_close
        ):
            raise NotImplementedError("Gate does not support remote close.")

        await self._send_action_callback(
            device_type=DeviceType.GATE,
            event=self.Command.CLOSE,
            device_id=self.id_,
        )
