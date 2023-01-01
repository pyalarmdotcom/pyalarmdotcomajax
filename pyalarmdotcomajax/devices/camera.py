"""Alarm.com camera."""
from __future__ import annotations

import logging

from . import BaseDevice, DesiredStateMixin

log = logging.getLogger(__name__)


class Camera(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com camera element."""

    # Cameras do not have a state.

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None
