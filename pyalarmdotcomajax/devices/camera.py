"""Alarm.com camera."""

from __future__ import annotations

import logging

from . import BaseDevice

log = logging.getLogger(__name__)


class Camera(BaseDevice):
    """Represent Alarm.com camera element."""
    _livestream: str
    def process_device_type_specific_data(self) -> None:
        """Process livestream json"""
        if not (raw_livestream := self._device_type_specific_data.get("raw_livestream")):
            return
        print (raw_livestream)
        self._livestream = raw_livestream["attributes"]["proxyUrl"]

    # Cameras do not have a state.

    malfunction = False
    @property
    def livestream(self) -> str | None:
        """Get livestream URL."""
        return self._livestream

