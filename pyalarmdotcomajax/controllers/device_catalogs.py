"""Alarm.com controller for systems."""

import logging

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.device_catalog import DeviceCatalog

log = logging.getLogger(__name__)


class DeviceCatalogController(BaseController[DeviceCatalog]):
    """Controller for systems."""

    resource_type = ResourceType.DEVICE_CATALOG
    _resource_class = DeviceCatalog
    _requires_target_ids = True
