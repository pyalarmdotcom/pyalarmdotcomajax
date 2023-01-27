"""Alarm.com sensor."""
from __future__ import annotations

from enum import Enum, IntEnum
import logging

from . import BaseDevice

log = logging.getLogger(__name__)


class Sensor(BaseDevice):
    """Represent Alarm.com sensor element."""

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

    class Subtype(IntEnum):
        """Library of identified ADC device types."""

        CONTACT_SENSOR = 1
        MOTION_SENSOR = 2
        SMOKE_DETECTOR = 5
        FREEZE_SENSOR = 8
        CO_DETECTOR = 6
        PANIC_BUTTON = 9
        FIXED_PANIC = 10
        SIREN = 14
        GLASS_BREAK_DETECTOR = 19
        CONTACT_SHOCK_SENSOR = 52
        PANEL_MOTION_SENSOR = 89
        PANEL_GLASS_BREAK_DETECTOR = 83
        PANEL_IMAGE_SENSOR = 68
        MOBILE_PHONE = 69
