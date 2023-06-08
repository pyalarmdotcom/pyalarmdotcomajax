"""Shared constants."""
from __future__ import annotations

from enum import Enum

# WEBSOCKETS: BEGIN
WS_EVENT = "ws_event"

# URLS: BEGIN
URL_BASE = "https://www.alarm.com/"
PROVIDER_INFO_TEMPLATE = "{}/web/api/appload"
TROUBLECONDITIONS_URL_TEMPLATE = "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
IMAGE_SENSOR_DATA_URL_TEMPLATE = "{}/web/api/imageSensor/imageSensorImages/getRecentImages"
IDENTITIES_URL_TEMPLATE = "{}/web/api/identities/{}"
# URLS: END


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
