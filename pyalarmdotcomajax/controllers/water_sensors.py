"""Alarm.com controller for water sensors."""

import logging
from types import MappingProxyType

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.sensor import SensorState
from pyalarmdotcomajax.models.water_sensor import WaterSensor
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import ResourceEventType

log = logging.getLogger(__name__)


class WaterSensorController(BaseController[WaterSensor]):
    """Controller for water sensors."""

    resource_type = ResourceType.WATER_SENSOR
    _resource_class = WaterSensor
    _event_state_map = MappingProxyType(
        {
            ResourceEventType.Opened: SensorState.WET,
            ResourceEventType.Closed: SensorState.DRY,
        }
    )
    _supported_resource_events = SupportedResourceEvents(events=[*_event_state_map.keys()])
