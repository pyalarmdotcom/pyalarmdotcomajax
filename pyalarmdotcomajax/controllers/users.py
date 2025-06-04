"""Session, login, and user management."""

import logging
from typing import TYPE_CHECKING

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.controllers.registry import CONTROLLER_REGISTRY
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.user import AvailableSystem, Dealer, Identity, Profile

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge


class IdentitiesController(BaseController[Identity]):
    """Controller for user identity."""

    resource_type = ResourceType.IDENTITY
    _resource_class = Identity
    _resource_url_override = "identities"


class ProfilesController(BaseController[Profile]):
    """Controller for user profile."""

    resource_type = ResourceType.PROFILE
    _resource_class = Profile

    def __init__(self, bridge: "AlarmBridge", data_provider: IdentitiesController) -> None:
        """Initialize profile controller."""
        super().__init__(bridge, data_provider)


class DealersController(BaseController[Dealer]):
    """Controller for user profile."""

    resource_type = ResourceType.DEALER
    _resource_class = Dealer
    _requires_target_ids = True


class AvailableSystemsController(BaseController[AvailableSystem]):
    """Controller for user identity."""

    resource_type = ResourceType.AVAILABLE_SYSTEM
    _resource_class = AvailableSystem

    @property
    def active_system_id(self) -> str | None:
        """Return the ID of the active system."""

        for system in self._resources.values():
            if system.attributes.is_selected:
                return system.id

        return None


# Register user controllers in the global controller registry.
CONTROLLER_REGISTRY[ResourceType.IDENTITY] = IdentitiesController
CONTROLLER_REGISTRY[ResourceType.PROFILE] = ProfilesController
CONTROLLER_REGISTRY[ResourceType.DEALER] = DealersController
CONTROLLER_REGISTRY[ResourceType.AVAILABLE_SYSTEM] = AvailableSystemsController
