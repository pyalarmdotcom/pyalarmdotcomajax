"""Alarm.com System"""
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


class System(BaseDevice):
    """Represent Alarm.com system element."""

    @property
    def unit_id(self) -> str | None:
        """Return device ID."""
        if not (raw_id := self._attribs_raw.get("unitId")):
            return str(raw_id)

        return None

    @property
    def read_only(self) -> None:
        """Non-actionable object."""
        return

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None
