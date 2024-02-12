"""Alarm.com controller for cameras."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.camera import Camera
from pyalarmdotcomajax.models.jsonapi import Resource

log = logging.getLogger(__name__)


class CameraController(BaseController[Camera]):
    """Controller for lights."""

    _resource_type = ResourceType.CAMERA
    _resource_class = Camera
    _resource_url_override = "video/devices/cameras"

    def _device_filter(self, data: list[Resource] | Resource) -> list[Resource] | Resource:
        """
        Only return Skybell HD cameras.

        We don't really support cameras (no images / streaming), we only support settings for the Skybell HD.
        """

        if isinstance(data, Resource):
            data = [data]

        return [resource for resource in data if resource.attributes.get("deviceModel") == "SKYBELLHD"]
