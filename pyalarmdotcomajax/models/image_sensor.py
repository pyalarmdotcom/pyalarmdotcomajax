"""Alarm.com model for image sensors."""

from dataclasses import dataclass, field

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
    is_image_sensor_deleted: bool = field(metadata={"description": "True if the device is deleted; False otherwise."})
    support_peek_in_now: bool = field(metadata={"description": "True if the device supports PeekInNow; False otherwise."})
    description: str = field(metadata={"description": "The name of the image sensor on the system."})
    can_view_images: bool = field(metadata={"description": "Can the currently logged in login view images for this sensor?"})

    # support_peek_in_next_motion: bool = field(metadata={"description": "True if the device supports PeekInNextMotion; False otherwise."})
    # hide_peek_in_next_motion_button: bool = field(metadata={"description": "Should we hide the peek in next motion button?"})
    # excluded_from_visual_verification: bool = field(metadata={"description": "Is the image sensor excluded from visual verification?"})
    # excluded_from_escalated_events: bool = field(metadata={"description": "Is the image sensor excluded from escalated events?"})
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
    image_src: str = field(metadata={"description": "URI for the image sensor image source."})
    description: str = field(metadata={"description": "The event description for this image upload."})
    timestamp: str = field(metadata={"description": "Time stamp of when the image was taken."})


@dataclass
class ImageSensorImage(AdcDeviceResource[ImageSensorImageAttributes]):
    """Image sensor image resource."""

    resource_type = ResourceType.IMAGE_SENSOR_IMAGE
    attributes_type = ImageSensorImageAttributes

    @property
    def image_sensor_id(self) -> str | None:
        """Image sensor ID."""

        return get_related_entity_id_by_key(self.api_resource, "imageSensor")
