"""Alarm.com model for partitions."""

from dataclasses import dataclass, field
from enum import Enum

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    AdcResourceAttributes,
    BaseManagedDeviceAttributes,
    ResourceType,
)
from pyalarmdotcomajax.util import get_all_related_entity_ids


class PartitionState(Enum):
    """Partition states."""

    # Hidden state is considered armed.

    UNKNOWN = 0
    DISARMED = 1
    ARMED_STAY = 2
    ARMED_AWAY = 3
    ARMED_NIGHT = 4
    HIDDEN = 5


class ExtendedArmingOptionItems(Enum):
    """Partition arming options."""

    # https://www.alarm.com/web/system/assets/customer-site/enums/ArmingOption.js

    BYPASS_SENSORS = 0
    NO_ENTRY_DELAY = 1
    SILENT_ARMING = 2
    NIGHT_ARMING = 3
    SELECTIVELY_BYPASS_SENSORS = 4
    # FORCE_ARM = 5
    # INSTANT_ARM = 6
    # STAY_ARM = 7
    # AWAY_ARM = 8


@dataclass
class ExtendedArmingOptions(AdcResourceAttributes):
    """
    Extended arming options.

    Can be either a list of valid options or a list of valid option combinations.
    """

    disarmed: list[ExtendedArmingOptionItems] | list[list[ExtendedArmingOptionItems]] | None = field(default=None)
    armed_stay: list[ExtendedArmingOptionItems] | list[list[ExtendedArmingOptionItems]] | None = field(default=None)
    armed_away: list[ExtendedArmingOptionItems] | list[list[ExtendedArmingOptionItems]] | None = field(default=None)
    armed_night: list[ExtendedArmingOptionItems] | list[list[ExtendedArmingOptionItems]] | None = field(default=None)


@dataclass
class PartitionAttributes(BaseManagedDeviceAttributes[PartitionState]):
    """Attributes of partition."""

    # fmt: off
    extended_arming_options: ExtendedArmingOptions = field(metadata={"description": "The supported extended arming options for each arming mode."})
    invalid_extended_arming_options: ExtendedArmingOptions = field(metadata={"description": "The combinations of extended arming options that are invalid for each arming mode."})
    can_bypass_sensor_when_armed: bool = field(metadata={"description": "Indicates if the panel supports bypass commands when armed."}, default=False)
    has_open_bypassable_sensors: bool = field(metadata={"description": "Indicates if the partition has any open sensors that can be bypassed."}, default=False)
    has_sensor_in_trouble_condition: bool = field(metadata={"description": "Indicates if the partition has any sensors in a trouble condition."}, default=False)
    hide_force_bypass: bool = field(metadata={"description": "Indicates if the force bypass checkbox should be hidden. If hidden, force bypass is always enabled."}, default=False)
    needs_clear_issues_prompt: bool = field(metadata={"description": "Indicates if the user should be prompted about any present issues before allowing arming."}, default=False)
    partition_id: str = field(metadata={"description": "The ID of this partition."}, default="1")
    has_active_alarm: bool = field(metadata={"description": "Indicates if the partition has an active alarm."}, default=False)
    has_only_arming: bool = field(metadata={"description": "Indicates if the partition only has a generic 'arm' options and not arm away and arm stay."}, default=False)
    # fmt: on

    @property
    def supports_night_arming(self) -> bool:
        """Return whether night arming is supported."""

        return ExtendedArmingOptionItems.NIGHT_ARMING in (self.extended_arming_options.armed_night or [])


@dataclass
class Partition(AdcDeviceResource[PartitionAttributes]):
    """Partition resource."""

    resource_type = ResourceType.PARTITION
    attributes_type = PartitionAttributes

    @property
    def items(self) -> set[str]:
        """Return list of child item IDs for this partition."""

        # Removes system ID from list of related entities.
        return get_all_related_entity_ids(self.api_resource) - set({self.system_id})
