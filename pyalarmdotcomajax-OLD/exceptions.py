"""Exceptions."""

from __future__ import annotations

from typing import Any

from .const import OtpType


class AlarmdotcomException(Exception):
    """Base exception for pyalarmdotcomajax."""

    pass


#
# DEVICE EXCEPTIONS
#
class DeviceException(AlarmdotcomException):
    """Base Alarm.com device exception."""

    pass


class UnsupportedDeviceType(DeviceException):
    """pyalarmdotcomajax encountered a device with a type not currently supported by the package."""

    def __init__(self, device_type: Any, device_id: str | None = None) -> None:
        """Initialize the exception."""

        if device_id:
            message = f"Encountered unsupported device type '{device_type!s}' with ID '{device_id}'."
        else:
            message = f"Encountered unsupported device type '{device_type!s}'."

        super().__init__(message)


class UnknownDevice(DeviceException):
    """pyalarmdotcomajax did not recognize the device ID."""

    def __init__(self, device_id: str) -> None:
        """Initialize the exception."""
        super().__init__(f"Unknown device ID '{device_id}'.")


#
# WEBSOCKET EXCEPTIONS
#
class UnsupportedWebSocketMessage(DeviceException):
    """Device does not support requested action."""

    def __init__(self, message: dict) -> None:
        """Initialize the exception."""
        super().__init__(f"Unsupported websocket message: {message}")


#
# SESSION EXCEPTIONS
#
class SessionException(AlarmdotcomException):
    """Base exception for pyalarmdotcomajax authentication and connectivity failures."""

    pass


class AuthenticationFailed(SessionException):
    """Raised when the server rejects a user's login credentials."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the exception."""
        super().__init__()

        self.can_autocorrect = kwargs.pop("can_autocorrect", False)


class OtpRequired(SessionException):
    """Raised during login if a user had two-factor authentication enabled."""

    def __init__(self, enabled_2fa_methods: list[OtpType]) -> None:
        """Initialize the exception."""
        super().__init__()

        self.enabled_2fa_methods = enabled_2fa_methods


class ConfigureTwoFactorAuthentication(SessionException):
    """Raised during login if the user gets the Alarm.com nag screen to setup 2 factor authentication."""

    def __init__(self) -> None:
        """Initialize the exception."""
        super().__init__(
            "Alarm.com requires that two-factor authentication be set up on your account. Please log in to"
            " Alarm.com and set up two-factor authentication."
        )


class SessionTimeout(AlarmdotcomException):
    """Raised when the user's session has timed out and needs to be re-established."""


class ServiceUnavailable(AlarmdotcomException):
    """Raised when multiple requests to the server have failed."""


class NotAuthorized(SessionException):
    """Raised when the user does not have permission to perform requested action."""


class TryAgain(SessionException):
    """Request that caller tries again after session has been fixed."""


#
# DATA EXCEPTIONS
#
class DataException(AlarmdotcomException):
    """Base Alarm.com data exception."""


class UnexpectedResponse(DataException):
    """Successfully received server response, but format is not as expected."""


#
# CLI EXCEPTIONS
#


class CliException(AlarmdotcomException):
    """Base Alarm.com CLI exception."""

    pass


class InvalidConfigurationOption(CliException):
    """Configuration option is not valid."""


#
# MISC EXCEPTIONS
#


class MiscException(AlarmdotcomException):
    """Base Alarm.com misc exception."""

    pass


class NotInitialized(MiscException):
    """Not initialized."""
