"""Alarm.com system."""
from __future__ import annotations

import logging

from . import BaseDevice

log = logging.getLogger(__name__)


class System(BaseDevice):
    """Represent Alarm.com system element."""

    read_only = True
    malfunction = False

    @property
    def unit_id(self) -> str | None:
        """Return device ID."""
        if not (raw_id := self.raw_attributes.get("unitId")):
            return str(raw_id)

        return None
