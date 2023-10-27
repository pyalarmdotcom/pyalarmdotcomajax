"""Alarm.com model for sensors."""

from dataclasses import dataclass, field
from enum import IntEnum

from pyalarmdotcomajax.models.base import (
    AdcResourceSubtype,
    AdcSubtypedResource,
    BaseManagedDeviceAttributes,
    ResourceType,
)


class SensorState(IntEnum):
    """Sensor states."""

    UNKNOWN = -1
    CLOSED = 1
    OPEN = 2
    IDLE = 3
    ACTIVE = 4
    DRY = 5
    WET = 6
    FULL = 7
    LOW = 8
    OPENED_CLOSED = 9
    ISSUE = 10
    OK = 11


class SensorSubtype(AdcResourceSubtype):
    """Library of identified ADC device types."""

    UNKNOWN = -1
    CONTACT_SENSOR = 1
    MOTION_SENSOR = 2
    SMOKE_DETECTOR = 5
    FREEZE_SENSOR = 8
    CO_DETECTOR = 6
    PANIC_BUTTON = 9
    FIXED_PANIC = 10
    SIREN = 14
    GLASS_BREAK_DETECTOR = 19
    CONTACT_SHOCK_SENSOR = 52
    PANEL_MOTION_SENSOR = 89
    PANEL_GLASS_BREAK_DETECTOR = 83
    PANEL_IMAGE_SENSOR = 68
    MOBILE_PHONE = 69

    @classmethod
    def _missing_(cls: type, value: object) -> AdcResourceSubtype:
        """Set default enum member if an unknown value is provided."""
        return SensorSubtype.UNKNOWN


@dataclass
class SensorAttributes(BaseManagedDeviceAttributes[SensorState]):
    """Attributes of sensor."""

    # fmt: off
    is_bypassed: bool = field(metadata={"description": "This sensor is bypassed."})
    is_flex_io: bool = field(metadata={"description": "This sensor is a flex IO sensor."})
    is_monitoring_enabled: bool = field(metadata={"description": "The sensor has normal activity monitoring enabled."})
    supports_bypass: bool = field(metadata={"description": "This sensor supports bypass."})
    supports_immediate_bypass: bool = field(metadata={"description": "This sensor supports bypass outside an arming event."})
    open_closed_status: int = field(metadata={"description":"This sensor is in an 'Open' or 'Closed' state."})
    device_type: SensorSubtype = field(metadata={"description": "The type of sensor."})
    # fmt: on


@dataclass
class Sensor(AdcSubtypedResource[SensorSubtype, SensorAttributes]):
    """Sensor resource."""

    resource_type = ResourceType.SENSOR
    attributes_type = SensorAttributes
    resource_subtypes = SensorSubtype
