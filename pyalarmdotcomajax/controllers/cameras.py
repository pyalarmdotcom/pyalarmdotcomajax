"""Alarm.com controller for cameras."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.camera import Camera
from pyalarmdotcomajax.models.jsonapi import JsonApiSuccessResponse, Resource

log = logging.getLogger(__name__)


class CameraController(BaseController[Camera]):
    """Controller for lights."""

    _resource_type = ResourceType.CAMERA
    _resource_class = Camera
    _resource_url = "{}web/api/video/devices/cameras/{}"

    def _device_filter(self, response: JsonApiSuccessResponse) -> JsonApiSuccessResponse:
        """
        Only return Skybell HD cameras.

        We don't really support cameras (no images / streaming), we only support settings for the Skybell HD.
        """

        if isinstance(response.data, Resource):
            response.data = [response.data]

        response.data = [
            resource for resource in response.data if resource.attributes.get("deviceModel") == "SKYBELLHD"
        ]

        return response
