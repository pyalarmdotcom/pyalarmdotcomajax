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
    """Extended arming options."""

    disarmed: list[ExtendedArmingOptionItems] | None = field(default=None)
    armed_stay: list[ExtendedArmingOptionItems] | None = field(default=None)
    armed_away: list[ExtendedArmingOptionItems] | None = field(default=None)
    armed_night: list[ExtendedArmingOptionItems] | None = field(default=None)


@dataclass
class PartitionAttributes(BaseManagedDeviceAttributes[PartitionState]):
    """Attributes of partition."""

    # fmt: off
    can_bypass_sensor_when_armed: bool = field(metadata={"description": "Indicates if the panel supports bypass commands when armed."})
    extended_arming_options: ExtendedArmingOptions = field(metadata={"description": "The supported extended arming options for each arming mode."})
    has_open_bypassable_sensors: bool = field(metadata={"description": "Indicates if the partition has any open sensors that can be bypassed."})
    has_sensor_in_trouble_condition: bool = field(metadata={"description": "Indicates if the partition has any sensors in a trouble condition."})
    hide_force_bypass: bool = field(metadata={"description": "Indicates if the force bypass checkbox should be hidden. If hidden, force bypass is always enabled."})
    invalid_extended_arming_options: ExtendedArmingOptions = field(metadata={"description": "The combinations of extended arming options that are invalid for each arming mode."})
    needs_clear_issues_prompt: bool = field(metadata={"description": "Indicates if the user should be prompted about any present issues before allowing arming."})
    partition_id: str = field(metadata={"description": "The ID of this partition."})
    has_active_alarm: bool = field(metadata={"description": "Indicates if the partition has an active alarm."})
    # fmt: on

    @property
    def supports_night_arming(self) -> bool:
        """Return whether night arming is supported."""

        return ExtendedArmingOptionItems.NIGHT_ARMING in (
            self.extended_arming_options.armed_night or []
        )


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
