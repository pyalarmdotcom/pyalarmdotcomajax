"""Session, login, and user management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.user import (
    AvailableSystem,
    Identity,
    Profile,
)

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge


class IdentitiesController(BaseController[Identity]):
    """Controller for user identity."""

    _resource_type = ResourceType.IDENTITY
    _resource_class = Identity
    _resource_url = "{}/web/api/identities/{}"


class ProfilesController(BaseController[Profile]):
    """Controller for user profile."""

    _resource_type = ResourceType.PROFILE
    _resource_class = Profile
    _resource_url = None

    def __init__(self, bridge: AlarmBridge, data_provider: IdentitiesController) -> None:
        """Initialize profile controller."""
        super().__init__(bridge, data_provider)


class AvailableSystemsController(BaseController[AvailableSystem]):
    """Controller for user identity."""

    _resource_type = ResourceType.AVAILABLE_SYSTEM
    _resource_class = AvailableSystem
    _resource_url = "{}web/api/systems/availableSystemItems"

    @property
    def active_system_id(self) -> str | None:
        """Return the ID of the active system."""

        for system in self._resources.values():
            if system.attributes.is_selected:
                return system.id

        return None
