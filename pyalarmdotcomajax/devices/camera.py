"""Alarm.com Camera"""
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


class Camera(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com camera element."""

    # Cameras do not have a state.

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None
