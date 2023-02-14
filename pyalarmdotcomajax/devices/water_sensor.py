"""Alarm.com water sensor."""
from __future__ import annotations

import logging

from .sensor import Sensor

log = logging.getLogger(__name__)

# Water sensors are just sensors by another name.


class WaterSensor(Sensor):
    """Represent Alarm.com water sensor element."""
