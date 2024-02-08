"""Alarm.com controller for systems."""

from __future__ import annotations

import logging

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.device_catalog import DeviceCatalog

log = logging.getLogger(__name__)


class DeviceCatalogController(BaseController[DeviceCatalog]):
    """Controller for systems."""

    _resource_type = ResourceType.DEVICE_CATALOG
    _resource_class = DeviceCatalog
    _resource_url = "{}web/api/settings/manageDevices/deviceCatalogs/{}"  # Substitute with base url and system ID.
    _requires_target_ids = True
