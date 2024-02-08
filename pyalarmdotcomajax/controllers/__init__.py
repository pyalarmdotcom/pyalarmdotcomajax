"""Alarm.com controllers."""

from collections.abc import Callable
from enum import Enum
from typing import TypeVar

from pyalarmdotcomajax.models.base import AdcResource


class EventType(Enum):
    """Resource event types for transmission from pyalarmdotcomajax."""

    RESOURCE_ADDED = "add"
    RESOURCE_UPDATED = "update"
    RESOURCE_DELETED = "delete"

AdcResourceT = TypeVar("AdcResourceT", bound=AdcResource)

EventCallBackType = Callable[
    [EventType, str, AdcResourceT | None], None
]  # EventType, resource_id, resource (optional)
