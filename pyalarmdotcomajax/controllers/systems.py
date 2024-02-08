"""Alarm.com controller for systems."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.system import System

log = logging.getLogger(__name__)


class SystemController(BaseController[System]):
    """Controller for lights."""

    _resource_type = ResourceType.SYSTEM
    _resource_class = System
    _resource_url = "{}web/api/systems/systems/{}"
