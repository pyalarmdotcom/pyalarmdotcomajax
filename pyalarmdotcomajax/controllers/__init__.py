"""Alarm.com controllers."""

from collections.abc import Callable
from enum import Enum
from typing import TypeVar

from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.models.extensions.base import ExtensionAttributes


class EventType(Enum):
    """Resource event types for transmission from pyalarmdotcomajax."""

    RESOURCE_ADDED = "add"
    RESOURCE_UPDATED = "update"
    RESOURCE_DELETED = "delete"


AdcResourceT = TypeVar("AdcResourceT", bound=AdcResource)
ExtensionAttributesT = TypeVar("ExtensionAttributesT", bound=ExtensionAttributes)


EventCallBackType = Callable[
    [EventType, str, AdcResourceT | None], None
]  # EventType, resource_id, resource (optional)

ExtensionEventCallbackType = Callable[
    [EventType, str, ExtensionAttributesT | None], None
]  # EventType, resource_id, extension_attributes (optional)
