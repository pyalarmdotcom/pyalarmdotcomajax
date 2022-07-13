"""Alarm.com Garage Door"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from enum import IntEnum
import logging
from typing import Any
from typing import final
from typing import Protocol
from typing import TypedDict

import aiohttp
from dateutil import parser
from pyalarmdotcomajax.errors import InvalidConfigurationOption
from pyalarmdotcomajax.errors import UnexpectedDataStructure
from pyalarmdotcomajax.extensions import CameraSkybellControllerExtension
from pyalarmdotcomajax.extensions import ConfigurationOption
from pyalarmdotcomajax.helpers import ExtendedEnumMixin
from . import (
    TroubleCondition,
    DeviceType,
    DEVICE_URLS,
    DesiredStateProtocol,
    DesiredStateMixin,
    ElementSpecificData,
    BaseDevice,
)

log = logging.getLogger(__name__)


class GarageDoor(DesiredStateMixin, BaseDevice):
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
