"""Exceptions."""
from __future__ import annotations


class UnsupportedDevice(Exception):
    """pyalarmdotcomajax encountered a device not currently supported by the package."""


class UnkonwnDevice(Exception):
    """pyalarmdotcomajax did not recognize the device ID."""


class AuthenticationFailed(Exception):
    """Alarm.com authentication failure."""


class TwoFactor_OtpRequired(Exception):
    """User has two factor authentication enabled."""


class TwoFactor_ConfigurationRequired(Exception):
    """Client encountered Alarm.com nag screen to setup 2 factor authentication."""


class DataFetchFailed(Exception):
    """General or connection error encountered when fetching data."""


class UnexpectedDataStructure(Exception):
    """Successfully received JSON object, but format is not as expected."""


class BadAccount(Exception):
    """Account can't lock in or major permissions issue."""


class DeviceTypeNotAuthorized(Exception):
    """Account does not have access to a specific device type."""


class InvalidConfigurationOption(Exception):
    """Configuration option is not valid."""


class UnsupportedAction(Exception):
    """Device does not support requested action."""


class TryAgain(Exception):
    """Request that caller tries again after session has been fixed."""
