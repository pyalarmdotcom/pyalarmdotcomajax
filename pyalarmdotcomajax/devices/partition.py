"""Alarm.com partition."""
from __future__ import annotations

from enum import Enum
import logging

from . import BaseDevice
from . import DesiredStateMixin
from . import DeviceType

log = logging.getLogger(__name__)


class Partition(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com partition element."""

    class DeviceState(Enum):
        """Enum of arming states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ArmingState.js

        UNKNOWN = 0
        DISARMED = 1
        ARMED_STAY = 2
        ARMED_AWAY = 3
        ARMED_NIGHT = 4

    class Command(Enum):
        """Commands for ADC partitions."""

        DISARM = "disarm"
        ARM_STAY = "armStay"
        ARM_AWAY = "armAway"

    @property
    def uncleared_issues(self) -> bool | None:
        """Return whether user needs to clear device state on alarm.com."""
        if isinstance(
            issues := self._attribs_raw.get("needsClearIssuesPrompt", None), bool
        ):
            return issues

        return None

    async def _async_arm(
        self,
        arm_type: Command,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
        night_arming: bool = False,
    ) -> None:
        """Arm alarm system."""

        if arm_type == self.Command.DISARM:
            log.error("Invalid arm type.")
            return

        msg_body = {
            "forceBypass": force_bypass,
            "noEntryDelay": no_entry_delay,
            "silentArming": silent_arming,
            "nightArming": night_arming,
        }

        await self._send_action_callback(
            device_type=DeviceType.PARTITION,
            event=arm_type,
            device_id=self.id_,
            msg_body=msg_body,
        )

    async def async_arm_stay(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm stay.")

        await self._async_arm(
            arm_type=self.Command.ARM_STAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=False,
        )

    async def async_arm_away(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm away.")

        await self._async_arm(
            arm_type=self.Command.ARM_AWAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=False,
        )

    async def async_arm_night(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm night.")

        await self._async_arm(
            arm_type=self.Command.ARM_STAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=True,
        )

    async def async_disarm(
        self,
    ) -> None:
        """Disarm alarm system."""

        log.debug("Calling disarm.")

        await self._send_action_callback(
            device_type=DeviceType.PARTITION,
            event=self.Command.DISARM,
            device_id=self.id_,
        )
