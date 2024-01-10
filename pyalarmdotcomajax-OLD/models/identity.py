"""Module containing dataclasses for identity-related objects."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import aiofiles
from mashumaro import field_options

from pyalarmdotcomajax.models.api import BaseElement, GenericEntity, GenericResponse

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class User:
    """Base object for resources returned from the gateway."""

    def __init__(self, identity_attributes: IdentityAttributes, profile_attributes: ProfileAttributes):
        """Initialize the resource."""

        self._raw_identity = identity_attributes
        self._raw_profile = profile_attributes

    @property
    def attributes(self) -> dict[str, Any]:
        """All attributes."""

        return {**self._raw_profile.to_dict(), **self._raw_identity.to_dict()}


#
# API IDENTITY RESPONSE
#


@dataclass
class IdentityAttributes(BaseElement):
    """Attributes of a raw identity response."""

    # fmt: off
    timezone: str = field(metadata=field_options(alias="timezone"))
    preferred_timezone: str = field(metadata=field_options(alias="preferredTimezone"))
    application_session_properties: ApplicationSessionProperties = field(metadata=field_options(alias="applicationSessionProperties"))
    use_celsius: bool = field(metadata=field_options(alias="localizeTempUnitsToCelsius"))
    can_access_trouble_conditions: bool | None = field(default=None, metadata=field_options(alias="hasTroubleConditionsService"))
    # fmt: on


IdentityResponse = GenericResponse[Literal["identity"], IdentityAttributes]


@dataclass
class ApplicationSessionProperties(BaseElement):
    """A class representing application session properties."""

    # fmt: off
    should_timeout: bool = field(metadata=field_options(alias="shouldTimeout"))  # Whether the session should timeout
    keep_alive_url: str = field(metadata=field_options(alias="keepAliveUrl"))  # URL for keep-alive requests
    enable_keep_alive: bool = field(metadata=field_options(alias="enableKeepAlive"))  # Whether keep-alive requests are enabled
    logout_timeout_ms: int = field(metadata=field_options(alias="logoutTimeoutMs"))  # Timeout for logout in milliseconds
    inactivity_warning_timeout_ms: int = field(metadata=field_options(alias="inactivityWarningTimeoutMs"))  # Timeout for inactivity warning in milliseconds
    # fmt: on


#
# API USER RESPONSE
#


@dataclass
class ProfileAttributes(BaseElement):
    """A class representing a user profile inclusion list entry."""

    email: str = field(metadata=field_options(alias="loginEmailAddress"))


ApiProfileResponse = GenericEntity[Literal["profile/profile"], ProfileAttributes]


async def main() -> None:
    """Run program within coroutine."""

    async with aiofiles.open("/workspaces/datamodel-generator/identity_rsp.json", "rb") as fin:
        json_rsp = await fin.read()
        IdentityResponse.from_json(json_rsp)


if __name__ == "__main__":
    asyncio.run(main())
2052
