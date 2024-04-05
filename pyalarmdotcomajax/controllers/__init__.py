"""Alarm.com controllers."""

from dataclasses import dataclass, field
from typing import TypeVar

from pyalarmdotcomajax.events import EventBrokerMessage
from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.models.jsonapi import (
    Resource,
    SuccessDocument,
)

AdcResourceT = TypeVar("AdcResourceT", bound=AdcResource)


#
# CONTROLLER EVENTS
#


@dataclass(kw_only=True)
class UpdatedResourceMessage(EventBrokerMessage):
    """Message class for updated resources."""

    id: str
    resource: AdcResource | None = None


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
