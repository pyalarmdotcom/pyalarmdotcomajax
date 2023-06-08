"""Alarm.com water sensor."""
from __future__ import annotations

import logging

from . import BaseDevice
from .sensor import Sensor

log = logging.getLogger(__name__)


class WaterSensor(Sensor):
    """Represent Alarm.com water sensor element."""

    class DeviceState(BaseDevice.DeviceState):
        """Enum of sensor states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/SensorStatus.js

        DRY = 5
        WET = 6
