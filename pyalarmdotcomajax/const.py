"""Shared constants."""

from __future__ import annotations

from collections import namedtuple
from enum import Enum
from typing import ClassVar, NamedTuple, Protocol

# CONFIG: BEGIN
REQUEST_RETRY_LIMIT = 3
SUBMIT_RETRY_LIMIT = 2
DEBUG_REQUEST_DUMP_MAX_LEN = 1000
# CONFIG: END


# URLS: BEGIN
URL_BASE = "https://www.alarm.com/"
API_URL_BASE = URL_BASE + "web/api/"

ATTR_STATE = "state"
ATTR_DESIRED_STATE = "desiredState"
# URLS: END


# EVENTS: BEGIN
class ListenerCallbackT(Protocol):
    """Function type for callback when an event occurs."""

    def __call__(self, device_id: str, event_type: ItemEvent, data: dict) -> None:
        """Send event notification to listeners via ADC controller."""
        ...


ListenerRegistryCallbackRecord: NamedTuple[ListenerCallbackT, str] = namedtuple(
    "ListenerRegistryCallbackRecord", ["callback_fn", "listener_name"]
)


class ItemEvent(Enum):
    """Enum for item events."""

    STATE_CHANGE = "state_change"
    FAILURE_GENERIC = "failure_generic"


# EVENTS: END


class ResponseTypes(Enum):
    """Response types."""

    JSON: ClassVar[dict] = {"Accept": "application/json", "charset": "utf-8"}
    JSONAPI: ClassVar[dict] = {"Accept": "application/vnd.api+json", "charset": "utf-8"}
    FORM: ClassVar[dict] = {"Content-Type": "application/x-www-form-urlencoded", "charset": "utf-8"}
    HTML: ClassVar[dict] = {"Accept": "text/html,application/xhtml+xml,application/xml"}
