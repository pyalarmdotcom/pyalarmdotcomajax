"""Alarm.com controller for partitions."""

from __future__ import annotations

import logging
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.exceptions import UnsupportedOperation
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.partition import ExtendedArmingOptionItems, Partition, PartitionState
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import ResourceEventType

log = logging.getLogger(__name__)


class PartitionCommand(StrEnum):
    """Commands for ADC partitions."""

    DISARM = "disarm"
    ARM_STAY = "armStay"
    ARM_AWAY = "armAway"


STATE_COMMAND_MAP = {
    PartitionState.DISARMED: PartitionCommand.DISARM,
    PartitionState.ARMED_STAY: PartitionCommand.ARM_STAY,
    PartitionState.ARMED_AWAY: PartitionCommand.ARM_AWAY,
    PartitionState.ARMED_NIGHT: PartitionCommand.ARM_STAY,  # Armed Night is Arm Stay with Night Arming extended option.
}

ARMING_EXTENSION_BODY_MAP = {
    ExtendedArmingOptionItems.BYPASS_SENSORS: {"forceBypass": True},
    ExtendedArmingOptionItems.NO_ENTRY_DELAY: {"noEntryDelay": True},
    ExtendedArmingOptionItems.SILENT_ARMING: {"silentArming": True},
    ExtendedArmingOptionItems.NIGHT_ARMING: {"nightArming": True},
}


# TODO: EventType.Alarm | EventType.PolicePanic:


class PartitionController(BaseController[Partition]):
    """Controller for partitions."""

    _resource_type = ResourceType.PARTITION
    _resource_class = Partition
    _event_state_map = MappingProxyType(
        {
            ResourceEventType.Disarmed: PartitionState.DISARMED,
            ResourceEventType.ArmedAway: PartitionState.ARMED_AWAY,
            ResourceEventType.ArmedStay: PartitionState.ARMED_STAY,
            ResourceEventType.ArmedNight: PartitionState.ARMED_NIGHT,
        }
    )
    _supported_resource_events = SupportedResourceEvents(events=[*_event_state_map.keys()])

    # Special handling of 422 status.
    # 422 sometimes occurs when forceBypass is True but there's nothing to bypass.

    def get_partition_id_from_resource_id(self, resource_id: str) -> str | None:
        """Get the partition to which a device belongs."""

        for partition in self.items:
            if resource_id in partition.items:
                return partition.id

        return None

    async def clear_faults(self, id: str) -> None:
        """Clear faults on partition."""

        await self._send_command(id, "clearIssues")

    async def disarm(self, id: str) -> None:
        """Disarm partition."""

        await self.set_state(id, PartitionState.DISARMED)

    async def arm_stay(
        self, id: str, force_bypass: bool = False, no_entry_delay: bool = False, silent_arming: bool = False
    ) -> None:
        """Arm partition in stay mode."""

        extended_arming_options = [
            ExtendedArmingOptionItems.BYPASS_SENSORS if force_bypass else None,
            ExtendedArmingOptionItems.NO_ENTRY_DELAY if no_entry_delay else None,
            ExtendedArmingOptionItems.SILENT_ARMING if silent_arming else None,
        ]

        await self.set_state(
            id, PartitionState.ARMED_STAY, [option for option in extended_arming_options if option]
        )

    async def arm_away(self, id: str, force_bypass: bool = False, no_entry_delay: bool = False) -> None:
        """Arm partition in away mode."""

        extended_arming_options = [
            ExtendedArmingOptionItems.BYPASS_SENSORS if force_bypass else None,
            ExtendedArmingOptionItems.NO_ENTRY_DELAY if no_entry_delay else None,
        ]

        await self.set_state(
            id, PartitionState.ARMED_AWAY, [option for option in extended_arming_options if option]
        )

    async def arm_night(self, id: str, force_bypass: bool = False, no_entry_delay: bool = False) -> None:
        """Arm partition in night mode."""

        extended_arming_options = [
            ExtendedArmingOptionItems.BYPASS_SENSORS if force_bypass else None,
            ExtendedArmingOptionItems.NO_ENTRY_DELAY if no_entry_delay else None,
            ExtendedArmingOptionItems.NIGHT_ARMING,
        ]

        await self.set_state(
            id, PartitionState.ARMED_NIGHT, [option for option in extended_arming_options if option]
        )

    async def set_state(
        self,
        id: str,
        state: PartitionState,
        extended_arming_options: list[ExtendedArmingOptionItems] | None = None,
    ) -> None:
        """Change partition state."""

        msg_body: dict[str, Any] = {}

        extended_arming_options = extended_arming_options or []

        # Disarm does not support extended arming options.
        if state == PartitionState.DISARMED and extended_arming_options:
            UnsupportedOperation("Extended arming options not supported for disarm.")

        # Add extended arming options to body.
        # Check that each requested arming option is supported for the partition.

        for option in extended_arming_options:
            if option in getattr(
                self[id].attributes.extended_arming_options, state.name.lower()
            ) and ARMING_EXTENSION_BODY_MAP.get(option):
                msg_body.update(ARMING_EXTENSION_BODY_MAP[option])
            else:
                raise UnsupportedOperation(f"Extended arming option {option} not supported for {state}.")

        if not (command := STATE_COMMAND_MAP.get(state)):
            raise UnsupportedOperation(f"State {state} not implemented.")

        await self._send_command(id, command.value, msg_body)

    async def change_sensor_bypass(
        self, partition_id: str, bypass_ids: list[str] | None = None, unbypass_ids: list[str] | None = None
    ) -> None:
        """Change sensor bypass state."""

        if not (bypass_ids or unbypass_ids):
            raise ValueError("Either bypass_ids or unbypass_ids must be provided.")

        await self._send_command(
            partition_id,
            "bypassSensors",
            {
                "bypass": "|".join(bypass_ids) if bypass_ids else "",
                "unbypass": "|".join(unbypass_ids) if unbypass_ids else "",
            },
        )
