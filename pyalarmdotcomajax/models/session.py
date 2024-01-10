"""Module containing dataclasses for identity-related objects."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from mashumaro import field_options

from pyalarmdotcomajax.const import TWO_FACTOR_TYPE, OtpType
from pyalarmdotcomajax.models.jsonapi import (
    BaseAttributes,
    BaseSupportedResource,
)

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class Session:
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
class ApplicationSessionProperties(BaseAttributes):
    """A class representing application session properties."""

    # fmt: off
    should_timeout: bool = field(metadata={"description": "Whether the session should timeout"})
    keep_alive_url: str = field(metadata={"description": "URL for keep-alive requests"})
    enable_keep_alive: bool = field(metadata={"description": "Whether keep-alive requests are enabled"})
    logout_timeout_ms: int = field(metadata={"description": "Timeout for logout in milliseconds"})
    inactivity_warning_timeout_ms: int = field(metadata={"description": "Timeout for inactivity warning in milliseconds"})
    # fmt: on


@dataclass
class IdentityAttributes(BaseAttributes):
    """Attributes of a raw identity response."""

    # fmt: off
    timezone: str
    preferred_timezone: str
    application_session_properties: ApplicationSessionProperties
    localize_temp_units_to_celsius: bool
    provider_name: str = field(metadata=field_options(alias="logo_name"))
    can_access_trouble_conditions: bool | None = field(default=None)
    # fmt: on


@dataclass
class Identity(BaseSupportedResource):
    """Identity resource."""

    type_ = "identity"
    attributes: IdentityAttributes


#
# API USER PROFILE RESPONSE
#


@dataclass
class ProfileAttributes(BaseAttributes):
    """A class representing a user profile inclusion list entry."""

    email: str = field(metadata=field_options(alias="login_email_address"))


@dataclass
class Profile(BaseSupportedResource):
    """Identity resource."""

    type_ = "profile/profile"
    attributes: ProfileAttributes


@dataclass
class SmsMobileNumber(BaseAttributes):
    """Attributes for a user's SMS mobile number."""

    mobile_number: str
    country: str
    cell_provider: str


@dataclass
class TwoFactorAuthenticationAttributes(BaseAttributes):
    """Attributes for a user's two factor authentication options."""

    sms_mobile_number: SmsMobileNumber | None
    email: str
    current_device_name: str
    is_current_device_trusted: bool
    selected_type_of_2fa: int
    enabled_two_factor_types: int
    valid_2fa_permissions: list[OtpType]
    can_reset_2fa: bool
    show_suggested_setup: bool
    can_skip_suggested_setup: bool


@dataclass
class TwoFactorAuthentication(BaseSupportedResource):
    """Object representing a user's two factor authentication options."""

    type_ = TWO_FACTOR_TYPE
    attributes: TwoFactorAuthenticationAttributes


# async def main() -> None:
#     """Run program within coroutine."""

#     async with aiofiles.open(
#         "/workspaces/pyalarmdotcomajax/tests/responses/identity_real_deleteme.json",
#         "r",
#         # "/workspaces/pyalarmdotcomajax/tests/responses/identities_ok.json",
#         # "r",
#     ) as fin:
#         json_rsp = await fin.read()

#         # print(json_rsp["data"][0]["attributes"])
#         response = JsonApiResponse.from_json(json_rsp)

#         if not isinstance(response, SuccessResponse):
#             return

#         identity = response.data[0]

#         print(identity)

#         # Extract user's profile
#         if response.included and isinstance(response.included, list):
#             for inclusion in response.included:
#                 if inclusion.type_ == "profile/profile":
#                     print(inclusion)

#     # print(response.data)


# if __name__ == "__main__":
#     asyncio.run(main())
