"""Module containing dataclasses for identity-related objects."""

from dataclasses import dataclass, field

from mashumaro import field_options

from pyalarmdotcomajax.models.base import AdcResource, AdcResourceAttributes, ResourceType
from pyalarmdotcomajax.util import get_related_entity_id_by_key

#
# API IDENTITY RESPONSE
#


@dataclass
class ApplicationSessionProperties(AdcResourceAttributes):
    """A class representing application session properties."""

    # fmt: off
    should_timeout: bool = field(metadata={"description": "Specifies if the session should timeout"})
    keep_alive_url: str = field(metadata={"description": "URL used for keep-alive requests"})
    enable_keep_alive: bool = field(metadata={"description": "Indicates whether keep-alive requests are enabled"})
    logout_timeout_ms: int = field(metadata={"description": "Timeout duration for logout in milliseconds"})
    inactivity_warning_timeout_ms: int = field(metadata={"description": "Timeout duration for inactivity warning in milliseconds"})
    # fmt: on


@dataclass
class IdentityAttributes(AdcResourceAttributes):
    """Attributes of a raw identity response."""

    # fmt: off
    timezone: str
    preferred_timezone: str
    application_session_properties: ApplicationSessionProperties
    localize_temp_units_to_celsius: bool
    provider_name: str = field(metadata=field_options(alias="logo_name"))
    has_trouble_conditions_service: bool
    # fmt: on


@dataclass
class Identity(AdcResource[IdentityAttributes]):
    """Identity resource."""

    resource_type = ResourceType.IDENTITY
    attributes_type = IdentityAttributes

    @property
    def provider_name(self) -> str | None:
        """The name of the Alarm.com provider."""
        return self.attributes.provider_name or None

    @property
    def keep_alive_url(self) -> str | None:
        """URL for keep-alive requests, if keep alive is enabled."""
        return (
            self.attributes.application_session_properties.keep_alive_url
            if self.attributes.application_session_properties.enable_keep_alive
            else None
        )

    @property
    def use_celsius(self) -> bool | None:
        """Whether the user uses celsius or fahrenheit."""
        return self.attributes.localize_temp_units_to_celsius or None

    @property
    def selected_system(self) -> str | None:
        """The ID of the selected system."""

        return get_related_entity_id_by_key(self.api_resource, "selected_system")


#
# API USER PROFILE RESPONSE
#


@dataclass
class ProfileAttributes(AdcResourceAttributes):
    """A class representing a user profile inclusion list entry."""

    email: str = field(metadata=field_options(alias="login_email_address"))


@dataclass
class Profile(AdcResource[ProfileAttributes]):
    """Identity resource."""

    resource_type = ResourceType.PROFILE
    attributes_type = ProfileAttributes


#
# API AVAILABLE SYSTEM RESPONSE
#


@dataclass
class AvailableSystemAttributes(AdcResourceAttributes):
    """Attributes for available systems."""

    name: str
    is_selected: bool


@dataclass
class AvailableSystem(AdcResource[AvailableSystemAttributes]):
    """Object representing available systems."""

    resource_type = ResourceType.AVAILABLE_SYSTEM
    attributes_type = AvailableSystemAttributes
