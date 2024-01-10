"""Shared constants."""

from __future__ import annotations

from collections import namedtuple
from enum import Enum
from typing import NamedTuple, Protocol

# CONFIG: BEGIN
KEEP_ALIVE_SIGNAL_INTERVAL_S = 60
SESSION_REFRESH_DEFAULT_INTERVAL_MS = 780000  # 13 minutes. Sessions expire at 15.
SCENE_REFRESH_INTERVAL_M = 60
REQUEST_RETRY_LIMIT = 3
# CONFIG: END

# WEBSOCKETS: BEGIN
WS_EVENT = "ws_event"
# WEBSOCKETS: END

# fmt: off
# URLS: BEGIN
URL_BASE = "https://www.alarm.com/"
PROVIDER_INFO_TEMPLATE = "{}/web/api/appload"
TROUBLECONDITIONS_URL_TEMPLATE = "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
IMAGE_SENSOR_DATA_URL_TEMPLATE = "{}/web/api/imageSensor/imageSensorImages/getRecentImages"
IDENTITIES_URL_TEMPLATE = "{}/web/api/identities/{}"
ALL_DEVICES_URL_TEMPLATE = "{}web/api/settings/manageDevices/deviceCatalogs/{}" # Substitute with base url and system ID.
ALL_SYSTEMS_URL_TEMPLATE = "{}web/api/systems/availableSystemItems?searchString="
ALL_RECENT_IMAGES_TEMPLATE = "{}web/api/imageSensor/imageSensorImages/getRecentImages"

LOGIN_URL = "https://www.alarm.com/login"
LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
LOGIN_2FA_POST_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/verifyTwoFactorCode"
LOGIN_2FA_DETAIL_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}"
LOGIN_2FA_TRUST_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/trustTwoFactorDevice"
LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaSms"
LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaEmail"
# URLS: END

# LOGIN & SESSION: BEGIN
LOGIN_TWO_FACTOR_COOKIE_NAME = "twoFactorAuthenticationId"
LOGIN_REMEMBERME_FIELD = "ctl00$ContentPlaceHolder1$loginform$chkRememberMe"
VIEWSTATE_FIELD = "__VIEWSTATE"
VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

KEEP_ALIVE_DEFAULT_URL = "/web/KeepAlive.aspx"
KEEP_ALIVE_URL_PARAM_TEMPLATE = "?timestamp={}"
KEEP_ALIVE_RENEW_SESSION_URL_TEMPLATE = "{}web/api/identities/{}/reloadContext"
# LOGIN & SESSION: END
# fmt: on

# NON-DEVICE TYPES: BEGIN
PROFILE_TYPE = "profile/profile"
TWO_FACTOR_TYPE = "twoFactorAuthentication/twoFactorAuthentication"
# NON-DEVICE TYPES: END


class OtpType(Enum):
    """Alarm.com two factor authentication type."""

    # https://www.alarm.com/web/system/assets/customer-ember/enums/TwoFactorAuthenticationType.js
    # Keep these lowercase. Strings.json in Home Assistant requires lowercase values.

    disabled = 0
    app = 1
    sms = 2
    email = 4


ATTR_STATE_TEXT = "displayStateText"
ATTR_MAC_ADDRESS = "mac_address"
ATTR_STATE = "state"
ATTR_DESIRED_STATE = "desiredState"


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
