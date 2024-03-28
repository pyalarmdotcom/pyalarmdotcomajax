"""Alarm.com controllers."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TypeVar

from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.models.extensions.base import ExtensionAttributes
from pyalarmdotcomajax.models.jsonapi import (
    Resource,
    SuccessDocument,
)

AdcResourceT = TypeVar("AdcResourceT", bound=AdcResource)
ExtensionAttributesT = TypeVar("ExtensionAttributesT", bound=ExtensionAttributes)


#
# CONTROLLER EVENTS
#
class EventType(Enum):
    """Resource event types for transmission from pyalarmdotcomajax."""

    RESOURCE_ADDED = "add"
    RESOURCE_UPDATED = "update"
    RESOURCE_DELETED = "delete"


EventCallBackType = Callable[
    [EventType, str, AdcResourceT | None], None
]  # EventType, resource_id, resource (optional)

ExtensionEventCallbackType = Callable[
    [EventType, str, ExtensionAttributesT | None], None
]  # EventType, resource_id, extension_attributes (optional)

#
# /CONTROLLER EVENTS
#


#
# JSON:API RESPONSE CLASSES
#
@dataclass
class AdcSuccessDocumentSingle(SuccessDocument):
    """Represent a successful response with a single primary resource object."""

    data: Resource
    included: list[Resource] = field(default_factory=list)


@dataclass
class AdcSuccessDocumentMulti(SuccessDocument):
    """Represent a successful response with multiple primary resource objects."""

    data: list[Resource]
    included: list[Resource] = field(default_factory=list)


#
# /JSON:API RESPONSE CLASSES
#
