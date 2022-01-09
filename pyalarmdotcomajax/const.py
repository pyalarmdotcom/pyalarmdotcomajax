"""Constants."""

from enum import Enum, IntEnum
from typing import List


class ExtendedEnumMixin(Enum):
    """Search and export-list functions to enums."""

    @classmethod
    def has_value(cls, value) -> bool:
        """Return whether value exists in enum."""
        return value in cls._value2member_map_

    @classmethod
    def list(cls) -> List:
        """Return list of all enum members."""
        return list(map(lambda c: c.value, cls))


class ADCRelationshipType(Enum):
    """Library of identified ADC device families."""

    SYSTEM = "systems/system"
    SENSOR = "devices/sensor"
    PARTITION = "devices/partition"
    LOCK = "devices/lock"
    GARAGE_DOOR = "devices/garage-door"

    # Not Supported
    # THERMOSTAT = "devices/thermostat"
    # CONFIGURATION = "systems/configuration"
    # LIGHT = "devices/light"
    # CAMERA = "video/camera"
    # GEO_DEVICE = "geolocation/geo-device"
    # GEO_FENCE = "geolocation/fence"
    # SCENE = "automation/scene"


class ADCDeviceType(ExtendedEnumMixin):
    """Enum of SUPPORTED devices using ADC ids."""

    SYSTEM = "systems"
    SENSOR = "sensors"
    PARTITION = "partitions"
    LOCK = "locks"
    GARAGE_DOOR = "garageDoors"

    # Not Supported
    # THERMOSTAT = "thermostats"
    # CONFIGURATION = "configuration"
    # LIGHT = "light"
    # CAMERA = "camera"
    # GEO_DEVICE = "geo-device"
    # GEO_FENCE = "fence"
    # SCENE = "scene"


class ADCSensorSubtype(IntEnum):
    """Library of identified ADC device types."""

    CONTACT_SENSOR = 1
    SMOKE_DETECTOR = 5
    CO_DETECTOR = 6
    PANIC_BUTTON = 9
    GLASS_BREAK_DETECTOR = 19


class PartitionCommand(Enum):
    """Commands for ADC partitions."""

    DISARM = "disarm"
    ARM_STAY = "armStay"
    ARM_AWAY = "armAway"


class LockCommand(Enum):
    """Commands for ADC locks."""

    LOCK = "lock"
    UNLOCK = "unlock"


class GarageDoorCommand(Enum):
    """Commands for ADC garage doors."""

    OPEN = "open"
    CLOSE = "close"
