"""Alarm.com image sensor."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
import logging
from typing import TypedDict

from dateutil import parser

from . import BaseDevice, DeviceType

log = logging.getLogger(__name__)


class ImageSensorImage(TypedDict):
    """Holds metadata for image sensor images."""

    id_: str
    image_b64: str
    image_src: str
    description: str
    timestamp: datetime


class ImageSensor(BaseDevice):
    """Represent Alarm.com image sensor element."""

    class Command(Enum):
        """Commands for ADC image sensors."""

        PEEK_IN = "doPeekInNow"

    _recent_images: list[ImageSensorImage] = []

    def process_element_specific_data(self) -> None:
        """Process recent images."""

        if not (
            raw_recent_images := self._element_specific_data.get("raw_recent_images")
        ):
            return

        for image in raw_recent_images:
            if (
                isinstance(image, dict)
                and str(
                    image.get("relationships", {})
                    .get("imageSensor", {})
                    .get("data", {})
                    .get("id")
                )
                == self.id_
            ):
                image_data: ImageSensorImage = {
                    "id_": image["id"],
                    "image_b64": image["attributes"]["image"],
                    "image_src": image["attributes"]["imageSrc"],
                    "description": image["attributes"]["description"],
                    "timestamp": parser.parse(image["attributes"]["timestamp"]),
                }
                self._recent_images.append(image_data)

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None

    @property
    def images(self) -> list[ImageSensorImage] | None:
        """Get a list of images taken by the image sensor."""

        return self._recent_images

    async def async_peek_in(self) -> None:
        """Send peek in command to take photo."""

        await self._send_action_callback(
            device_type=DeviceType.IMAGE_SENSOR,
            event=self.Command.PEEK_IN,
            device_id=self.id_,
        )
