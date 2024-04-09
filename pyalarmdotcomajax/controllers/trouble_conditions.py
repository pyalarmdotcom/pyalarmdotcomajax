"""Alarm.com controller for trouble conditions."""

from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.trouble_condition import TroubleCondition


class TroubleConditionController(BaseController[TroubleCondition]):
    """Controller for trouble conditions."""

    resource_type = ResourceType.TROUBLE_CONDITION
    _resource_class = TroubleCondition
