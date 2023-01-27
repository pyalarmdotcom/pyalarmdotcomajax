"""Alarm.com water sensor."""
from __future__ import annotations

from enum import Enum
import logging

from . import BaseDevice

log = logging.getLogger(__name__)

# Water sensors are just sensors by another name.


class WaterSensor(BaseDevice):
    """Represent Alarm.com water sensor element."""

    class DeviceState(Enum):
        """Enum of sensor states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/SensorStatus.js

        UNKNOWN = 0
        CLOSED = 1
        OPEN = 2
        IDLE = 3
        ACTIVE = 4
        DRY = 5
        WET = 6

        # Below not currently supported.
        # FULL = 7
        # LOW = 8
        # OPENED_CLOSED = 9
        # ISSUE = 10
        # OK = 11
