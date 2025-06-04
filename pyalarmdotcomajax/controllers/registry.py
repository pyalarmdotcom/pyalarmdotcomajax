"""Global registry for Alarm.com controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyalarmdotcomajax.models.base import ResourceType  # noqa: TC001

if TYPE_CHECKING:
    from .base import BaseController

# Map ResourceType to controller class
CONTROLLER_REGISTRY: dict[ResourceType, type[BaseController]] = {}

