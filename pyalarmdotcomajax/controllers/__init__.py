"""Alarm.com controllers."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.events import EventBrokerMessage
from pyalarmdotcomajax.models.jsonapi import (
    Resource,
    SuccessDocument,
)

if TYPE_CHECKING:
    from pyalarmdotcomajax.models.base import AdcResource

AdcControllerT = TypeVar("AdcControllerT", bound=BaseController)

#
# CONTROLLER EVENTS
#


@dataclass(kw_only=True)
class ResourceEventMessage(EventBrokerMessage):
    """Message class for updated resources."""

    id: str
    resource: "AdcResource | None" = None


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
