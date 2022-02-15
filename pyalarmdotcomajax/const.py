"""Constants."""
from __future__ import annotations

from datetime import datetime
from enum import Enum, IntEnum
from typing import Any, TypedDict

TWO_FACTOR_COOKIE_NAME = "twoFactorAuthenticationId"


class AuthResult(Enum):
    """Standard for reporting results of login attempt."""

    SUCCESS = "success"
    OTP_REQUIRED = "otp_required"
    ENABLE_TWO_FACTOR = "enable_two_factor"


class ArmingOption(Enum):
    """Specify when to force bypass device problems."""

    STAY = "stay"
    AWAY = "away"
    ALWAYS = "true"
    NEVER = "false"


class ExtendedEnumMixin(Enum):
    """Search and export-list functions to enums."""

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Return whether value exists in enum."""
        return value in cls._value2member_map_

    @classmethod
    def list(cls) -> list:
        """Return list of all enum members."""

        def get_enum_value(enum_class: Enum) -> Any:
            """Mypy choked when this was expressed as a lambda."""
            return enum_class.value

        return list(map(get_enum_value, cls))


class ADCTroubleCondition(TypedDict):
    """Alarm.com alert / trouble condition."""

    message_id: str
    title: str
    body: str
    device_id: str


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
    IMAGE_SENSOR = "imageSensors"

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
    MOTION_SENSOR = 2
    SMOKE_DETECTOR = 5
    CO_DETECTOR = 6
    PANIC_BUTTON = 9
    GLASS_BREAK_DETECTOR = 19
    PANEL_MOTION_SENSOR = 89

    
class ADCPartitionCommand(Enum):
    """Commands for ADC partitions."""

    DISARM = "disarm"
    ARM_STAY = "armStay"
    ARM_AWAY = "armAway"
    ARM_NIGHT = "armNight"


class ADCLockCommand(Enum):
    """Commands for ADC locks."""

    LOCK = "lock"
    UNLOCK = "unlock"


class ADCGarageDoorCommand(Enum):
    """Commands for ADC garage doors."""

    OPEN = "open"
    CLOSE = "close"


class ADCImageSensorCommand(Enum):
    """Commands for ADC image sensors."""

    peekIn = "doPeekInNow"


class ElementSpecificData(TypedDict, total=False):
    """Hold entity-type-specific metadata."""

    images: list[ImageData] | None


class ImageData(TypedDict):
    """Holds metadata for image sensor images."""

    id_: str
    image_b64: str
    image_src: str
    description: str
    timestamp: datetime


# class DeviceTypeFetchErrors(TypedDict, total=False):
#     """Store all errors encountered when fetching devices."""

#     systems: DeviceTypeFetchError | None
#     partitions: DeviceTypeFetchError | None
#     locks: DeviceTypeFetchError | None
#     sensors: DeviceTypeFetchError | None
#     garageDoors: DeviceTypeFetchError | None


# class DeviceTypeFetchError(TypedDict):
#     """Store errors encountered when fetching a particular device type."""

#     device_type: ADCDeviceType
#     errors: list[ADCError]


# class ADCError(TypedDict):
#     """Alarm.com response error format."""

#     status: str
#     detail: str
#     code: str
