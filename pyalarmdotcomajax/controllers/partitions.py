"""Alarm.com controller for partitions."""

# ruff: noqa: UP007 FBT002 FBT001

import logging
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Any, Optional

import typer

from pyalarmdotcomajax.adc.util import Param_Id, cli_action
from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.exceptions import UnsupportedOperation
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.partition import (
    ExtendedArmingOptionItems,
    Partition,
    PartitionState,
)
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


# TODO: EventBrokerTopic.Alarm | EventBrokerTopic.PolicePanic:


class PartitionController(BaseController[Partition]):
    """Controller for partitions."""

    resource_type = ResourceType.PARTITION
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

    def get_device_partition(self, resource_id: str) -> str | None:
        """Get the partition to which a device belongs."""

        for partition in self.items:
            if resource_id in partition.items:
                return partition.id

        return None

    @cli_action()
    async def clear_faults(self, id: Param_Id) -> None:
        """Clear all faults on a partition."""

        await self._send_command(id, "clearIssues")

    @cli_action()
    async def disarm(self, id: Param_Id) -> None:
        """Disarm a partition."""

        await self.set_state(id, PartitionState.DISARMED)

    @cli_action()
    async def arm_stay(
        self,
        id: Param_Id,
        force_bypass: Annotated[
            bool, typer.Option(help="Bypass all open zones before arming.", show_default=False)
        ] = False,
        no_entry_delay: Annotated[
            bool,
            typer.Option(
                help="Bypass entry delay. This will sound the alarm immediately when an entry zone triggers.",
                show_default=False,
            ),
        ] = False,
        silent_arming: Annotated[
            bool,
            typer.Option(
                help="Arm the system without emitting arming \\ exit delay tones at the panel.", show_default=False
            ),
        ] = False,
    ) -> None:
        """Arm a partition in stay mode."""

        extended_arming_options = [
            ExtendedArmingOptionItems.BYPASS_SENSORS if force_bypass else None,
            ExtendedArmingOptionItems.NO_ENTRY_DELAY if no_entry_delay else None,
            ExtendedArmingOptionItems.SILENT_ARMING if silent_arming else None,
        ]

        await self.set_state(
            id, PartitionState.ARMED_STAY, [option for option in extended_arming_options if option]
        )

    @cli_action()
    async def arm_away(self, id: str, force_bypass: bool = False, no_entry_delay: bool = False) -> None:
        """Arm a partition in away mode."""

        extended_arming_options = [
            ExtendedArmingOptionItems.BYPASS_SENSORS if force_bypass else None,
            ExtendedArmingOptionItems.NO_ENTRY_DELAY if no_entry_delay else None,
        ]

        await self.set_state(
            id, PartitionState.ARMED_AWAY, [option for option in extended_arming_options if option]
        )

    @cli_action()
    async def arm_night(self, id: str, force_bypass: bool = False, no_entry_delay: bool = False) -> None:
        """Arm a partition in night mode."""

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
        extended_arming_options: Optional[list[ExtendedArmingOptionItems]] = None,
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

    @cli_action()
    async def change_sensor_bypass(
        self, partition_id: str, bypass_ids: Optional[list[str]] = None, unbypass_ids: Optional[list[str]] = None
    ) -> None:
        """Bypass or unbypass sensors on a partition."""

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
