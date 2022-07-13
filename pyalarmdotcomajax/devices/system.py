"""Alarm.com system."""
from __future__ import annotations

import logging

from . import BaseDevice

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
