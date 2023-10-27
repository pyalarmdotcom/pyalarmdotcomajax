"""Authentication models."""

from dataclasses import dataclass, field
from enum import Enum

from mashumaro import field_options

from pyalarmdotcomajax.models.base import (
    AdcResource,
    AdcResourceAttributes,
    ResourceType,
)


class OtpType(Enum):
    """Alarm.com two factor authentication type."""

    # https://www.alarm.com/web/system/assets/customer-ember/enums/TwoFactorAuthenticationType.js
    # Keep these lowercase. Strings.json in Home Assistant requires lowercase values.

    disabled = 0
    app = 1
    sms = 2
    email = 4


@dataclass
class SmsMobileNumber(AdcResourceAttributes):
    """Attributes for a user's SMS mobile number."""

    mobile_number: str
    country: str
    cell_provider: str


@dataclass
class TwoFactorAuthenticationAttributes(AdcResourceAttributes):
    """Attributes for a user's two factor authentication options."""

    sms_mobile_number: SmsMobileNumber | None
    current_device_name: str
    selected_type_of_2fa: int = field(
        metadata=field_options(alias="selected_type_of2_fa")
    )
    enabled_two_factor_types: int
    valid2fa_permissions: list[OtpType] = field(
        metadata=field_options(alias="valid2_fa_permissions")
    )
    show_suggested_setup: bool
    can_skip_suggested_setup: bool
    is_current_device_trusted: bool = False
    can_reset_2fa: bool = field(
        metadata=field_options(alias="can_reset2_fa"), default=False
    )
    email: str = ""


@dataclass
class TwoFactorAuthentication(AdcResource[TwoFactorAuthenticationAttributes]):
    """Object representing a user's two factor authentication options."""

    resource_type = ResourceType.TWO_FACTOR
    attributes_type = TwoFactorAuthenticationAttributes
