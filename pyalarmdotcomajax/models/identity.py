"""Module containing dataclasses for identity-related objects."""

# datamodel-codegen --input identity_resp.json --input-file-type json --output identity.py --output-model-type pydantic_v2.BaseModel --use-standard-collections --use-union-operator --capitalise-enum-members --allow-extra-fields  --reuse-model  --target-python-version 3.11 --use-double-quotes --snake-case-field

# datamodel-codegen --input identity_resp.json --input-file-type json --output identity.py --output-model-type msgspec.Struct --use-standard-collections --use-union-operator --capitalise-enum-members --allow-extra-fields  --reuse-model  --target-python-version 3.11 --use-double-quotes --snake-case-field

from __future__ import annotations

import asyncio
import logging
from typing import Literal

import aiofiles
from pydantic import BaseModel, ConfigDict, Field

from pyalarmdotcomajax.models.api import ApiEntity, ApiResponse

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class User:
    """Base object for resources returned from the gateway."""

    def __init__(self, identity_attributes: ApiIdentityAttributes, profile_attributes: ApiProfileAttributes):
        """Initialize the resource."""

        self._raw_identity = identity_attributes
        self._raw_profile = profile_attributes

    @property
    def attributes(self) -> str:
        """All attributes."""

        return {**self._raw_profile, **self._raw_identity}


#
# API IDENTITY RESPONSE
#


class ApiIdentityAttributes(BaseModel):
    """Attributes of a raw identity response."""

    model_config = ConfigDict(
        extra="allow",
    )
    timezone: str = Field(alias="timezone")
    preferred_timezone: str = Field(alias="preferredTimezone")
    can_access_trouble_conditions: bool | None = Field(alias="hasTroubleConditionsService", default=None)
    application_session_properties: ApiApplicationSessionProperties = Field(alias="applicationSessionProperties")
    use_celsius: bool = Field(alias="localizeTempUnitsToCelsius")


IdentityResponse = type[ApiResponse[Literal["identity"], ApiIdentityAttributes]]


class ApiApplicationSessionProperties(BaseModel):
    """A class representing application session properties."""

    model_config = ConfigDict(
        extra="allow",
    )
    should_timeout: bool = Field(alias="shouldTimeout")  # Whether the session should timeout
    keep_alive_url: str = Field(alias="keepAliveUrl")  # URL for keep-alive requests
    enable_keep_alive: bool = Field(alias="enableKeepAlive")  # Whether keep-alive requests are enabled
    logout_timeout_ms: int = Field(alias="logoutTimeoutMs")  # Timeout for logout in milliseconds
    inactivity_warning_timeout_ms: int = Field(
        alias="inactivityWarningTimeoutMs"
    )  # Timeout for inactivity warning in milliseconds


#
# API USER RESPONSE
#


class ApiProfileAttributes(BaseModel):
    """A class representing a user profile inclusion list entry."""

    model_config = ConfigDict(
        extra="allow",
    )
    email: str = Field(alias="loginEmailAddress")


ApiProfileResponse = type[ApiEntity[Literal["profile/profile"], ApiProfileAttributes]]


async def main() -> None:
    """Run program within coroutine."""

    async with aiofiles.open("/workspaces/datamodel-generator/identity_rsp.json", "rb") as fin:
        json_rsp = await fin.read()
        IdentityResponse(json_rsp)


if __name__ == "__main__":
    asyncio.run(main())
