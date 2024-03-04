"""Alarm.com model for cameras."""

from dataclasses import dataclass, field

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    AdcNamedDeviceAttributes,
    ResourceType,
)


@dataclass
class CameraAttributes(AdcNamedDeviceAttributes):
    """Attributes of camera."""

    # fmt: off
    # description: str = field(metadata={"description": "Device name"})
    battery_level_null: int | None = field(metadata={"description": "The current device battery level with null as the default value."})
    critical_battery: bool = field(metadata={"description": "Whether the device has a critical battery status."})
    low_battery: bool = field(metadata={"description": "Whether the device has a low battery status."})
    is_malfunctioning: bool = field(metadata={"description": "Is the camera currently set to a malfunction state."})

    is_unreachable: bool = field(metadata={"description": "Is the camera unreachable?"})
    firmware_version: str | None = field(metadata={"description": "The device firmware version."})
    public_ip: str | None = field(metadata={"description": "The device public IP address."})
    private_ip: str | None = field(metadata={"description": "The device private IP address."})
    # fmt: on


@dataclass
class Camera(AdcDeviceResource[CameraAttributes]):
    """Image sensor image resource."""

    resource_type = ResourceType.CAMERA
    attributes_type = CameraAttributes
