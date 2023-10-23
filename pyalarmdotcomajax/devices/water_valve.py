"""Alarm.com water valve."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.devices import DeviceType

from . import BaseDevice

log = logging.getLogger(__name__)


class WaterValve(BaseDevice):
    """Represent Alarm.com sensor element."""

    class DeviceState(BaseDevice.DeviceState):
        """Enum of water valve states."""

        # https://www.alarm.com/web/system/assets/customer-site/enums/WaterValveStatus.js

        UNKNOWN = 0
        CLOSED = 1
        OPEN = 2

    class Command(BaseDevice.Command):
        """Commands for ADC water valves."""

        OPEN = "open"
        CLOSE = "close"

    @property
    def models(self) -> dict:
        """Return mapping of known ADC model IDs to manufacturer and model name."""
        return {
            9361: {
                "manufacturer": "Qolsys",
                "model": "IQ Water Valve",
            }  # OEM is Custos - Z-Wave Ball Valve Servo US/CA
        }

    async def async_open(self) -> None:
        """Send open command."""

        await self.async_handle_external_desired_state_change(self.DeviceState.OPEN)

        await self._send_action(
            device_type=DeviceType.WATER_VALVE,
            event=self.Command.OPEN,
            device_id=self.id_,
        )

    async def async_close(self) -> None:
        """Send close command."""

        await self.async_handle_external_desired_state_change(self.DeviceState.CLOSED)

        await self._send_action(
            device_type=DeviceType.WATER_VALVE,
            event=self.Command.CLOSE,
            device_id=self.id_,
        )
