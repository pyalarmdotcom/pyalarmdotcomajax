"""Alarm.com model for gates."""

from dataclasses import dataclass, field
from enum import IntEnum

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    BaseManagedDeviceAttributes,
    ResourceType,
)


class GateState(IntEnum):
    """Enum of gate states."""

    # https://www.alarm.com/web/system/assets/customer-ember/enums/GateStatus.js

    UNKNOWN = 0
    OPEN = 1
    CLOSED = 2


@dataclass
class GateAttributes(BaseManagedDeviceAttributes[GateState]):
    """Attributes of a gate device."""

    supports_remote_close: float = field(
        metadata={"description": "Specifies whether the gate can be closed remotely."}
    )


@dataclass
class Gate(AdcDeviceResource[GateAttributes]):
    """Gate resource."""

    resource_type = ResourceType.GATE
    attributes_type = GateAttributes
