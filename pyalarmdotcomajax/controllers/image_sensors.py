"""Alarm.com controller for image sensors."""

import logging
from enum import StrEnum

from pyalarmdotcomajax.adc.util import Param_Id, cli_action
from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.image_sensor import ImageSensor, ImageSensorImage

log = logging.getLogger(__name__)


class ImageSensorCommand(StrEnum):
    """Commands for ADC image sensors."""

    PEEK_IN = "doPeekInNow"


class ImageSensorController(BaseController[ImageSensor]):
    """Controller for image sensors."""

    resource_type = ResourceType.IMAGE_SENSOR
    _resource_class = ImageSensor

    @cli_action()
    async def peek_in(self, id: Param_Id) -> None:
        """Take a peek in photo."""

        await self._send_command(id, ImageSensorCommand.PEEK_IN)


class ImageSensorImageController(BaseController[ImageSensorImage]):
    """Controller for image sensor images."""

    resource_type = ResourceType.IMAGE_SENSOR_IMAGE
    _resource_class = ImageSensorImage
    _resource_url_override = "imageSensor/imageSensorImages/getRecentImages"
