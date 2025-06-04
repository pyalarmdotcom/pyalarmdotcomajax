"""Orchestrator for image sensor resources."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyalarmdotcomajax.events import EventBrokerMessage, EventBrokerTopic, ResourceEventMessage
from pyalarmdotcomajax.models.image_sensor import ImageSensor, ImageSensorImage
from pyalarmdotcomajax.websocket.messages import EventWSMessage, ResourceEventType

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge

log = logging.getLogger(__name__)


class ImageSensorOrchestrator:
    """Coordinate image sensors and their images."""

    def __init__(self, bridge: AlarmBridge) -> None:
        self._bridge = bridge
        self._bridge.events.subscribe(EventBrokerTopic.RAW_RESOURCE_EVENT, self._on_ws_event)
        self._bridge.events.subscribe([
            EventBrokerTopic.RESOURCE_ADDED,
            EventBrokerTopic.RESOURCE_UPDATED,
        ], self._on_image_event)

    async def _on_ws_event(self, message: EventBrokerMessage) -> None:
        """Handle websocket events for image uploads."""

        if not isinstance(message, ResourceEventMessage):
            return
        resource = message.resource
        if not isinstance(resource, ImageSensor):
            return
        ws_msg = getattr(message, "ws_message", None)
        if isinstance(ws_msg, EventWSMessage) and ws_msg.subtype == ResourceEventType.ImageSensorUpload:
            await self._refresh_images(resource.id)

    async def _on_image_event(self, message: EventBrokerMessage) -> None:
        """Link new images to their parent sensors."""

        if not isinstance(message, ResourceEventMessage):
            return
        if not isinstance(message.resource, ImageSensorImage):
            return
        sensor_id = message.resource.image_sensor_id
        if sensor_id is None:
            return
        sensor = self._bridge.image_sensors.get(sensor_id)
        if sensor:
            await sensor._on_new_image([message.resource])  # noqa: SLF001

    async def _refresh_images(self, sensor_id: str) -> None:
        """Refresh images for a sensor and update sensor state."""

        await self._bridge.image_sensor_images.initialize([sensor_id])
        images = [
            image
            for image in self._bridge.image_sensor_images.items
            if image.image_sensor_id == sensor_id
        ]
        sensor = self._bridge.image_sensors.get(sensor_id)
        if sensor:
            await sensor._on_new_image(images)  # noqa: SLF001
