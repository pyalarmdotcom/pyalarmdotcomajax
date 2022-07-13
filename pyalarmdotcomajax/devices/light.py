"""Alarm.com Light"""
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


class Light(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com light element."""

    class DeviceState(Enum):
        """Enum of light states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LightStatus.js

        OFFLINE = 0
        NOSTATE = 1
        ON = 2
        OFF = 3
        LEVELCHANGE = 4

    class Command(Enum):
        """Commands for ADC lights."""

        ON = "turnOn"
        OFF = "turnOff"

    @property
    def available(self) -> bool:
        """Return whether the light can be manipulated."""
        return (
            self._attribs_raw.get("canReceiveCommands", False)
            and self._attribs_raw.get("remoteCommandsEnabled", False)
            and self._attribs_raw.get("hasPermissionToChangeState", False)
            and self.state
            in [self.DeviceState.ON, self.DeviceState.OFF, self.DeviceState.LEVELCHANGE]
        )

    @property
    def brightness(self) -> int | None:
        """Return light's brightness."""
        if not self._attribs_raw.get("isDimmer", False):
            return None

        if isinstance(level := self._attribs_raw.get("lightLevel", 0), int):
            return level

        return None

    @property
    def supports_state_tracking(self) -> bool | None:
        """Return whether the light reports its current state."""

        if isinstance(supports := self._attribs_raw.get("stateTrackingEnabled"), bool):
            return supports

        return None

    async def async_turn_on(self, brightness: int | None = None) -> None:
        """Send turn on command with optional brightness."""

        msg_body: dict | None = None
        if brightness:
            msg_body = {}
            msg_body["dimmerLevel"] = brightness

        await self._send_action_callback(
            device_type=DeviceType.LIGHT,
            event=self.Command.ON,
            device_id=self.id_,
            msg_body=msg_body,
        )

    async def async_turn_off(self) -> None:
        """Send turn off command."""

        await self._send_action_callback(
            device_type=DeviceType.LIGHT,
            event=self.Command.OFF,
            device_id=self.id_,
        )
