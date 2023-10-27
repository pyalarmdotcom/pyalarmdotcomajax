"""Alarm.com model for image sensors."""

from dataclasses import dataclass, field
from typing import ClassVar

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    AdcResourceAttributes,
    ResourceType,
)
from pyalarmdotcomajax.util import get_related_entity_id_by_key


@dataclass
class ImageSensorAttributes(AdcResourceAttributes):
    """
    Attributes of an image sensor.

    Image sensors don't have states.
    """

    # fmt: off
    is_image_sensor_deleted: bool = field(metadata={"description": "Indicates whether the device has been deleted."})
    support_peek_in_now: bool = field(metadata={"description": "Indicates whether the device supports PeekInNow feature."})
    can_view_images: bool = field(metadata={"description": "Specifies whether the currently logged in user can view images for this sensor."})

    # support_peek_in_next_motion: bool = field(metadata={"description": "Indicates whether the device supports
    # PeekInNextMotion feature."})
    # fmt: on


@dataclass
class ImageSensor(AdcDeviceResource[ImageSensorAttributes]):
    """Image sensor resource."""

    resource_type = ResourceType.IMAGE_SENSOR
    attributes_type = ImageSensorAttributes


@dataclass
class ImageSensorImageAttributes(AdcResourceAttributes):
    """Image sensor image attributes."""

    image: str = field(metadata={"description": "The Base64 encoded image."})
    image_src: str = field(
        metadata={"description": "URI for the image sensor image source."}
    )
    timestamp: str = field(
        metadata={"description": "Time stamp of when the image was taken."}
    )


@dataclass
class ImageSensorImage(AdcDeviceResource[ImageSensorImageAttributes]):
    """Image sensor image resource."""

    resource_type = ResourceType.IMAGE_SENSOR_IMAGE
    attributes_type = ImageSensorImageAttributes
    has_related_system: ClassVar[bool] = False

    @property
    def image_sensor_id(self) -> str | None:
        """Image sensor ID."""

        return get_related_entity_id_by_key(self.api_resource, "image_sensor")
