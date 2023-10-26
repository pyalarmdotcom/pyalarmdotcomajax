"""Alarm.com partition."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from . import BaseDevice, DeviceType

log = logging.getLogger(__name__)


class Partition(BaseDevice):
    """Represent Alarm.com partition element."""

    class ExtendedArmingOption(Enum):
        """Enum of extended arming options."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ArmingOption.js

        BYPASS_SENSORS = 0
        NO_ENTRY_DELAY = 1
        SILENT_ARMING = 2
        NIGHT_ARMING = 3
        SELECTIVE_BYPASS = 4

    @dataclass
    class ExtendedArmingMapping:
        """Map of which extended arming states apply to which arming types."""

        disarm: list[Partition.ExtendedArmingOption | None]
        arm_stay: list[Partition.ExtendedArmingOption | None]
        arm_away: list[Partition.ExtendedArmingOption | None]
        arm_night: list[Partition.ExtendedArmingOption | None]

    @dataclass
    class PartitionAttributes(BaseDevice.DeviceAttributes):
        """Partition attributes."""

        extended_arming_options: Partition.ExtendedArmingMapping  # List of extended arming options

    class DeviceState(BaseDevice.DeviceState):
        """Enum of arming states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ArmingState.js

        UNKNOWN = 0
        DISARMED = 1
        ARMED_STAY = 2
        ARMED_AWAY = 3
        ARMED_NIGHT = 4

    class Command(BaseDevice.Command):
        """Commands for ADC partitions."""

        DISARM = "disarm"
        ARM_STAY = "armStay"
        ARM_AWAY = "armAway"

    @property
    def uncleared_issues(self) -> bool | None:
        """Return whether user needs to clear device state on alarm.com."""
        if isinstance(issues := self.raw_attributes.get("needsClearIssuesPrompt", None), bool):
            return issues

        return None

    async def _async_arm(
        self,
        arm_type: Command,
        extended_arming_options: list[Partition.ExtendedArmingOption | None],
        force_bypass: bool | None = None,
        no_entry_delay: bool | None = None,
        silent_arming: bool | None = None,
        night_arming: bool | None = None,
    ) -> None:
        """Arm alarm system."""

        if arm_type == self.Command.DISARM:
            log.exception("Invalid arm type.")
            return

        msg_body = {}

        if force_bypass and Partition.ExtendedArmingOption.BYPASS_SENSORS in extended_arming_options:
            msg_body.update({"forceBypass": force_bypass})

        if no_entry_delay and Partition.ExtendedArmingOption.NO_ENTRY_DELAY in extended_arming_options:
            msg_body.update({"noEntryDelay": no_entry_delay})

        if silent_arming and Partition.ExtendedArmingOption.SILENT_ARMING in extended_arming_options:
            msg_body.update({"silentArming": silent_arming})

        if night_arming and Partition.ExtendedArmingOption.NIGHT_ARMING in extended_arming_options:
            msg_body.update({"nightArming": night_arming})

        await self._send_action(
            device_type=DeviceType.PARTITION,
            event=arm_type,
            device_id=self.id_,
            msg_body=msg_body,
        )

    @property
    def supports_night_arming(self) -> bool | None:
        """Return whether night arming is supported."""

        if Partition.ExtendedArmingOption.NIGHT_ARMING in self.attributes.extended_arming_options.arm_night:
            return True

        return False

    async def async_arm_stay(
        self,
        force_bypass: bool | None = None,
        no_entry_delay: bool | None = None,
        silent_arming: bool | None = None,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm stay.")

        await self.async_handle_external_desired_state_change(self.DeviceState.ARMED_STAY)

        await self._async_arm(
            arm_type=self.Command.ARM_STAY,
            extended_arming_options=self.attributes.extended_arming_options.arm_stay,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
        )

    async def async_arm_away(
        self,
        force_bypass: bool | None = None,
        no_entry_delay: bool | None = None,
        silent_arming: bool | None = None,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm away.")

        await self.async_handle_external_desired_state_change(self.DeviceState.ARMED_AWAY)

        await self._async_arm(
            arm_type=self.Command.ARM_AWAY,
            extended_arming_options=self.attributes.extended_arming_options.arm_away,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
        )

    async def async_arm_night(
        self,
        force_bypass: bool | None = None,
        no_entry_delay: bool | None = None,
        silent_arming: bool | None = None,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm night.")

        await self.async_handle_external_desired_state_change(self.DeviceState.ARMED_NIGHT)

        await self._async_arm(
            arm_type=self.Command.ARM_STAY,
            extended_arming_options=self.attributes.extended_arming_options.arm_night,
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

        await self.async_handle_external_desired_state_change(self.DeviceState.DISARMED)

        await self._send_action(
            device_type=DeviceType.PARTITION,
            event=self.Command.DISARM,
            device_id=self.id_,
        )

    def _get_extended_arming_options(self, options_list: list) -> list[Partition.ExtendedArmingOption | None]:
        """Convert raw extended arming options to ExtendedArmingOption."""

        return [self.ExtendedArmingOption(option) for option in options_list]

    @property
    def attributes(self) -> PartitionAttributes:
        """Return partition attributes."""

        extended_arming_options = dict(self.raw_attributes.get("extendedArmingOptions", {}))

        return self.PartitionAttributes(
            extended_arming_options=self.ExtendedArmingMapping(
                disarm=self._get_extended_arming_options(extended_arming_options.get("Disarmed", [])),
                arm_stay=self._get_extended_arming_options(extended_arming_options.get("ArmedStay", [])),
                arm_away=self._get_extended_arming_options(extended_arming_options.get("ArmedAway", [])),
                arm_night=self._get_extended_arming_options(extended_arming_options.get("ArmedNight", [])),
            )
        )
