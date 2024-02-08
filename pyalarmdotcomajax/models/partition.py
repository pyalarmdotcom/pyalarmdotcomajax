"""Alarm.com model for partitions."""

from dataclasses import dataclass, field
from enum import IntEnum

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    AdcResourceAttributes,
    BaseManagedDeviceAttributes,
    ResourceType,
)
from pyalarmdotcomajax.util import get_all_related_entity_ids


class PartitionState(IntEnum):
    """Partition states."""

    UNKNOWN = 0
    DISARMED = 1
    ARMED_STAY = 2
    ARMED_AWAY = 3
    ARMED_NIGHT = 4
    HIDDEN = 5


class ExtendedArmingOptionItems(IntEnum):
    """Partition arming options."""

    BYPASS_SENSORS = 0
    NO_ENTRY_DELAY = 1
    SILENT_ARMING = 2
    NIGHT_ARMING = 3
    SELECTIVELY_BYPASS_SENSORS = 4
    FORCE_ARM = 5
    INSTANT_ARM = 6
    STAY_ARM = 7
    AWAY_ARM = 8


@dataclass
class ExtendedArmingOptions(AdcResourceAttributes):
    """Extended arming options."""

    disarmed: list[ExtendedArmingOptionItems]
    armed_stay: list[ExtendedArmingOptionItems]
    armed_away: list[ExtendedArmingOptionItems]
    armed_night: list[ExtendedArmingOptionItems]


@dataclass
class PartitionAttributes(BaseManagedDeviceAttributes[PartitionState]):
    """Attributes of partition."""

    # fmt: off
    can_bypass_sensor_when_armed: bool = field(metadata={"description": "Indicates the panel supports sending bypass commands when the panel is armed."})
    extended_arming_options: ExtendedArmingOptions = field(metadata={"description": "The extended arming options supported per arming mode."})
    has_open_bypassable_sensors: bool = field(metadata={"description": "Indicates whether the partition has any open sensors related to 'Force Bypass' option."})
    has_sensor_in_trouble_condition: bool = field(metadata={"description": "Indicates whether the partition has any trouble condition related to 'Force Bypass' option."})
    hide_force_bypass: bool = field(metadata={"description": "Indicates whether the force bypass checkbox should be hidden. If hidden, force bypass is always enabled."})
    invalid_extended_arming_options: ExtendedArmingOptions = field(metadata={"description": "The extended arming option combinations that are invalid for each arming mode."})
    needs_clear_issues_prompt: bool = field(metadata={"description": "Should we prompt about present issues before allowing the user to arm?"})
    partition_id: str = field(metadata={"description": "The ID for this partition."})

    # can_access_panel_wifi: bool  # Can this partition access panel-wifi route?
    # can_enable_alexa: bool  # Can this partition enable Alexa features?
    # dealer_enforces_force_bypass: bool  # Indicates whether to warn the user if a sensor is open while trying to arm the panel.
    # is_alexa_enabled: bool  # Are Alexa features enabled on this partition?
    # sensor_naming_format: int  # The allowed device naming format.
    # show_new_force_bypass: bool  # Indicates whether we show the new force bypass with new text
    # fmt: on

    @property
    def supports_night_arming(self) -> bool:
        """Return whether night arming is supported."""

        return ExtendedArmingOptionItems.NIGHT_ARMING in self.extended_arming_options.armed_night


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
