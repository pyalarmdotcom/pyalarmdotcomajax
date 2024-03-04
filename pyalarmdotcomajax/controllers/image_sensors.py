"""Alarm.com controller for image sensors."""

from __future__ import annotations

import logging
from enum import StrEnum

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.image_sensor import ImageSensor, ImageSensorImage

log = logging.getLogger(__name__)


class ImageSensorCommand(StrEnum):
    """Commands for ADC image sensors."""

    PEEK_IN = "doPeekInNow"


class ImageSensorController(BaseController[ImageSensor]):
    """Controller for image sensors."""

    _resource_type = ResourceType.IMAGE_SENSOR
    _resource_class = ImageSensor

    async def peek_in(self, id: str) -> None:
        """Send peek in command to take photo."""

        await self._send_command(id, ImageSensorCommand.PEEK_IN)


class ImageSensorImageController(BaseController[ImageSensorImage]):
    """Controller for image sensor images."""

    _resource_type = ResourceType.IMAGE_SENSOR_IMAGE
    _resource_class = ImageSensorImage
    _resource_url_override = "imageSensor/imageSensorImages/getRecentImages"
