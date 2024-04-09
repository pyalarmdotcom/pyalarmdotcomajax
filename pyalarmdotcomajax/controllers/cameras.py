"""Alarm.com controller for cameras."""

import logging

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.camera import Camera
from pyalarmdotcomajax.models.jsonapi import Resource

log = logging.getLogger(__name__)


class CameraController(BaseController[Camera]):
    """Controller for lights."""

    resource_type = ResourceType.CAMERA
    _resource_class = Camera
    _resource_url_override = "video/devices/cameras"

    def _device_filter(self, data: list[Resource] | Resource) -> list[Resource] | Resource:
        """
        Only return Skybell HD cameras.

        We don't really support cameras (no images / streaming), we only support settings for the Skybell HD.
        """

        if isinstance(data, Resource):
            data = [data]

        # TODO: Make this work.
        # return [resource for resource in data if is_skybell(resource)]
        return []

    async def _post_init(self) -> None:
        """Post init hook."""

        # self._skybell_controller = SkybellExtensionController(self._bridge)
