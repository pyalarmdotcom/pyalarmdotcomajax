"""Alarm.com model for locks."""

from dataclasses import dataclass, field
from enum import IntEnum

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    BaseManagedDeviceAttributes,
    ResourceType,
)


class LockState(IntEnum):
    """Lock states."""

    UNKNOWN = 0
    LOCKED = 1
    UNLOCKED = 2
    HIDDEN = 3


@dataclass
class LockAttributes(BaseManagedDeviceAttributes[LockState]):
    """Attributes of lock."""

    # fmt: off
    supports_latch_control: bool = field(metadata={"description": "Whether the lock supports remotely controlling the latch."})

    # available_temporary_access_codes: int | None = field(metadata={"description": "The number of available Temporary Access Codes that were pushed to the locks on the unit."})
    # can_enable_remote_commands: bool = field(metadata={"description": "Can the remote commands be enabled or disabled? (Only for control point locks)"})
    # max_user_code_length: int = field(metadata={"description": "The maximum user code length this lock supports."})
    # supports_scheduled_user_codes: bool = field(metadata={"description": "Whether the lock supports scheduled user code programming."})
    # supports_temporary_user_codes: bool = field(metadata={"description": "Whether the lock supports temporary user code programming."})
    # total_temporary_access_codes: int | None = field(metadata={"description": "The total number of Temporary Access Codes that were pushed to the locks."})
    # fmt: on


@dataclass
class Lock(AdcDeviceResource[LockAttributes]):
    """Lock resource."""

    resource_type = ResourceType.LOCK
    attributes_type = LockAttributes
