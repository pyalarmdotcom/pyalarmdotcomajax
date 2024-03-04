"""Base controller for extensions."""

from __future__ import annotations

import logging
from abc import ABC
from asyncio import Task
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Self, TypeVar

from pyalarmdotcomajax.controllers.base import Generic
from pyalarmdotcomajax.models.extensions.base import Extension

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge

# TODO: Code here should be shared with BaseController.

ExtensionT = TypeVar("ExtensionT", bound=Extension)


class BaseExtensionController(Generic[ExtensionT], ABC):
    """Base controller for extensions."""

    def __init__(self, bridge: AlarmBridge) -> None:
        """Initialize controller object."""
        self._bridge = bridge

        self._resources: dict[str, ExtensionT] = {}

        # Holds references to asyncio tasks to prevent them from being garbage collected before completion.
        self._background_tasks: set[Task] = set()

    async def initialize(self) -> None:
        """Initialize the extension."""

        raise NotImplementedError()

    async def _refresh(self) -> None:
        """Refresh the extension data."""

        raise NotImplementedError()

    ####################
    # OBJECT FUNCTIONS #
    ####################

    def get(self, id: str, default: Any = None) -> Self | Any | None:
        """Return resource by ID."""
        return self._resources.get(id, default)

    def __getitem__(self, id: str) -> ExtensionT:
        """Return resource by ID."""
        return self._resources[id]

    def __iter__(self) -> Iterator[ExtensionT]:
        """Iterate over resources."""
        return iter(self._resources.values())

    def __contains__(self, id: str) -> bool:
        """Return whether resource is present."""
        return id in self._resources
