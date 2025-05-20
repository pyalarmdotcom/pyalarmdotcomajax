"""Alarm.com controller for image sensors."""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import StrEnum
from typing import TYPE_CHECKING

from pyalarmdotcomajax.adc.util import Param_Id, cli_action
from pyalarmdotcomajax.controllers.base import BaseController, device_controller
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.image_sensor import ImageSensor, ImageSensorImage
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import (
    BaseWSMessage,
    EventWSMessage,
    ResourceEventType,
)

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge
    from pyalarmdotcomajax.models import AdcResourceT

log = logging.getLogger(__name__)


class ImageSensorCommand(StrEnum):
    """Commands for ADC image sensors."""

    PEEK_IN = "doPeekInNow"


@device_controller(ResourceType.IMAGE_SENSOR, ImageSensor)
class ImageSensorController(BaseController[ImageSensor]):
    """Controller for image sensors."""

    _supported_resource_events = SupportedResourceEvents(
        events=[ResourceEventType.ImageSensorUpload]
    )

    def __init__(
        self,
        bridge: AlarmBridge,
        data_provider: BaseController | None = None,
        target_device_ids: list[str] | None = None,
        get_images_fn: Callable[[str], list[ImageSensorImage] | None] = lambda x: None,
    ) -> None:
        """Initialize the controller."""

        self._get_images_fn = get_images_fn
        super().__init__(bridge, data_provider, target_device_ids)

    @cli_action()
    async def peek_in(self, id: Param_Id) -> None:
        """Take a peek in photo."""

        await self._send_command(id, ImageSensorCommand.PEEK_IN)

    async def _inject_attributes(self, resource: ImageSensor) -> ImageSensor:
        """Inject image attributes into image sensor."""

        if not (images := self._get_images_fn(resource.id)):
            return resource

        # Get the latest image by checking for the most recent time stamp for an image associated with this image sensor.
        # Filter images to only those associated with this image sensor's id
        filtered_images = [
            image for image in images if image.image_sensor_id == resource.id
        ]
        if not filtered_images:
            return resource

        latest_image = max(
            filtered_images, key=lambda image: image.attributes.timestamp
        )

        # Check if the latest image is different from the current one
        if (
            resource.attributes.latest_image
            and resource.attributes.latest_image.id == latest_image.id
        ):
            return resource

        resource.attributes.latest_image = latest_image

        return resource

    async def _handle_event(
        self, adc_resource: AdcResourceT, message: BaseWSMessage
    ) -> AdcResourceT:
        """
        Handle events for image sensor images.

        Updates attributes on ResourceEventType.ImageSensorUpload.
        """

        log.debug(
            "Handling event for image sensor %s: %s",
            adc_resource.id,
            message,
        )

        if (
            isinstance(message, EventWSMessage)
            and message.subtype == ResourceEventType.ImageSensorUpload
            and message.value is not None
        ):
            adc_resource.api_resource.attributes.update(
                image=message.value,
                image_src=message.subvalue,
                timestamp=message.event_date_utc.isoformat(),
            )

        return adc_resource


class ImageSensorImageController(BaseController[ImageSensorImage]):
    """Controller for image sensor images."""

    resource_type = ResourceType.IMAGE_SENSOR_IMAGE
    _resource_class = ImageSensorImage
    _resource_url_override = "imageSensor/imageSensorImages/getRecentImages"

    def get_images_by_sensor(self, id: str) -> list[ImageSensorImage]:
        """Get images by sensor ID."""

        return [image for image in self.items if image.image_sensor_id == id]
