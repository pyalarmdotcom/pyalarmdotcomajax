"""Shared constants."""

from __future__ import annotations

from collections import namedtuple
from enum import Enum
from typing import ClassVar, NamedTuple, Protocol

# CONFIG: BEGIN
SCENE_REFRESH_INTERVAL_M = 60
REQUEST_RETRY_LIMIT = 3
SUBMIT_RETRY_LIMIT = 2
# CONFIG: END

# WEBSOCKETS: BEGIN
WS_EVENT = "ws_event"
# WEBSOCKETS: END

# fmt: off
# URLS: BEGIN
URL_BASE = "https://www.alarm.com/"
API_URL_BASE = URL_BASE + "web/api/"
# PROVIDER_INFO_TEMPLATE = "{}/web/api/appload"
# TROUBLECONDITIONS_URL_TEMPLATE = "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
# IMAGE_SENSOR_DATA_URL_TEMPLATE = "{}/web/api/imageSensor/imageSensorImages/getRecentImages"


# ALL_RECENT_IMAGES_TEMPLATE = "{}web/api/imageSensor/imageSensorImages/getRecentImages"



# URLS: END

# LOGIN & SESSION: BEGIN
# LOGIN_TWO_FACTOR_COOKIE_NAME = "twoFactorAuthenticationId"
# LOGIN_REMEMBERME_FIELD = "ctl00$ContentPlaceHolder1$loginform$chkRememberMe"
# VIEWSTATE_FIELD = "__VIEWSTATE"
# VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
# EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
# PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

# KEEP_ALIVE_DEFAULT_URL = "/web/KeepAlive.aspx"
# KEEP_ALIVE_URL_PARAM_TEMPLATE = "?timestamp={}"
# KEEP_ALIVE_RENEW_SESSION_URL_TEMPLATE = "{}web/api/identities/{}/reloadContext"
# LOGIN & SESSION: END
# fmt: on


# ATTR_STATE_TEXT = "displayStateText"
# ATTR_MAC_ADDRESS = "mac_address"
ATTR_STATE = "state"
ATTR_DESIRED_STATE = "desiredState"


class ResponseTypes(Enum):
    """Response types."""

    JSON: ClassVar[dict] = {"Accept": "application/json", "charset": "utf-8"}
    JSONAPI: ClassVar[dict] = {"Accept": "application/vnd.api+json", "charset": "utf-8"}
    FORM: ClassVar[dict] = {"Content-Type": "application/x-www-form-urlencoded", "charset": "utf-8"}
    HTML: ClassVar[dict] = {"Accept": "text/html,application/xhtml+xml,application/xml"}


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
