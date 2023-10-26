"""Alarm.com camera."""

from __future__ import annotations

import logging

from . import HardwareDevice

log = logging.getLogger(__name__)


class Camera(HardwareDevice):
    """Represent Alarm.com camera element."""

    # Cameras do not have a state.

    malfunction = False
