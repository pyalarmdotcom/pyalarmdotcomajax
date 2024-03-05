"""Alarm.com model for systems."""

from dataclasses import dataclass

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    AdcNamedDeviceAttributes,
    ResourceType,
)


@dataclass
class SystemAttributes(AdcNamedDeviceAttributes):
    """Attributes of alarm system."""

    has_snap_shot_cameras: bool
    supports_secure_arming: bool
    remaining_image_quota: int
    system_group_name: str
    unit_id: str
    access_control_current_system_mode: int
    is_in_partial_lockdown: bool
    icon: str


@dataclass
class System(AdcDeviceResource[SystemAttributes]):
    """System resource."""

    resource_type = ResourceType.SYSTEM
    attributes_type = SystemAttributes
