"""Defines pyalarmdotcomajax components."""

from enum import Enum
import logging
from types import FunctionType

from .const import (
    ADCDeviceType,
    ADCGarageDoorCommand,
    ADCLockCommand,
    ADCPartitionCommand,
    ADCRelationshipType,
    ADCSensorSubtype,
)

log = logging.getLogger(__name__)

#
# Mixins
#


class DesiredStateMixin:
    """Mixin decorator for mismatched_states function."""

    @property
    def mismatched_states(self) -> bool:
        """Return whether actual state is equal to desired state. False indicates problem."""
        return self.desired_state != self.state

    @property
    def desired_state(self) -> Enum:
        """Return state."""

        if self.has_state:
            try:
                state = self.DeviceState(self._attribs_raw.get("desiredState"))
            except ValueError:
                return None
            else:
                return state
        else:
            return None


#
# ADC Core Elements
#


class ADCBaseElement:
    """Contains properties shared by all ADC devices."""

    def __init__(
        self,
        send_action_callback: FunctionType,
        id_: str,
        attribs_raw: dict,
        subordinates: list,
        parent_ids: dict = None,
        family_raw: str = None,
    ) -> None:
        """Initialize base element class."""
        self._id_: str = id_
        self._family_raw: str = family_raw
        self._attribs_raw: dict = attribs_raw
        self._parent_ids: dict = parent_ids
        self._send_action_callback: FunctionType = send_action_callback
        self._subordinates: list = subordinates

        if parent_ids:
            self._system_id: str = parent_ids.get("system")
            self._partition_id: str = parent_ids.get("partition")
            self._parent_id_: str = parent_ids.get("parent_device")

        log.debug(
            "Initialized %s (%s) %s", self.device_type, self._family_raw, self.name
        )

    class DeviceState(Enum):
        """Placeholder for child device states."""

    @property
    def id_(self) -> str:
        """Return device ID."""
        return self._id_

    @property
    def name(self) -> None or str:
        """Return user-assigned device name."""
        return self._attribs_raw.get("description", None)

    @property
    def device_type(self) -> None or str:
        """Return normalized device type constant. E.g.: sensor, thermostat, etc."""
        try:
            return ADCRelationshipType(self._family_raw)
        except ValueError:
            return None

    @property
    def has_state(self) -> bool:
        """Return whether entity reports state."""
        return self._attribs_raw.get("hasState", False)

    @property
    def state(self) -> str or bool or DeviceState:
        """Return state."""

        if self.has_state:
            try:
                state = self.DeviceState(self._attribs_raw.get("state"))
            except ValueError:
                return None
            else:
                return state
        else:
            return None

    @property
    def battery_low(self) -> bool:
        """Return whether battery is low."""
        return self._attribs_raw.get("lowBattery", None)

    @property
    def battery_critical(self) -> bool:
        """Return whether battery is critically low."""
        return self._attribs_raw.get("criticalBattery", None)

    @property
    def system_id(self) -> str:
        """Return ID of device's parent system."""
        return self._parent_ids.get("system", None)

    @property
    def partition_id(self) -> str:
        """Return ID of device's parent partition."""
        return self._parent_ids.get("partition", None)

    @property
    def malfunction(self) -> bool:
        """Return whether device is malfunctioning."""
        return self._attribs_raw.get("isMalfunctioning", True) or self.state is None

    @property
    def mac_address(self) -> bool:
        """Return device MAC address."""
        return self._attribs_raw.get("macAddress")

    @property
    def raw_state_text(self) -> bool:
        """Return state description as reported by ADC."""
        return self._attribs_raw.get("displayStateText")

    def is_subordinate(self, device_id: str) -> bool:
        """Return whether submitted device is downstream from this device."""
        return [i_id for i_id in self._subordinates if i_id[0] == device_id]


class ADCSystem(ADCBaseElement):
    """Represent Alarm.com system element."""

    @property
    def unit_id(self) -> str:
        """Return device ID."""
        return self._attribs_raw.get("unitId", None)


class ADCPartition(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com partition element."""

    class DeviceState(Enum):
        """Enum of arming states."""

        UNKNOWN = 0
        DISARMED = 1
        ARMED_STAY = 2
        ARMED_AWAY = 3
        ARMED_NIGHT = 4

    @property
    def uncleared_issues(self) -> bool or None:
        """Return whether user needs to clear device state from alarm or device malfunction."""
        return self._attribs_raw.get("needsClearIssuesPrompt", None)

    async def async_alarm_disarm(self) -> None:
        """Send disarm command."""
        await self._send_action_callback(
            ADCDeviceType.PARTITION,
            ADCPartitionCommand.DISARM,
            self._id_,
        )

    async def async_alarm_arm_stay(self) -> None:
        """Send arm stay command."""

        await self._send_action_callback(
            ADCDeviceType.PARTITION,
            ADCPartitionCommand.ARM_STAY,
            self._id_,
        )

    async def async_alarm_arm_away(self) -> None:
        """Send arm away command."""

        await self._send_action_callback(
            ADCDeviceType.PARTITION,
            ADCPartitionCommand.ARM_AWAY,
            self._id_,
        )

    async def async_alarm_arm_night(self) -> None:
        """Send arm away command."""

        await self._send_action_callback(
            ADCDeviceType.PARTITION,
            ADCPartitionCommand.ARM_NIGHT,
            self._id_,
        )


class ADCLock(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com partition element."""

    class DeviceState(Enum):
        """Enum of lock states."""

        FAILED = "Failed"
        LOCKED = "Locked"
        UNLOCKED = "Open"

    async def async_lock(self):
        """Send lock command."""
        await self._send_action_callback(
            ADCDeviceType.LOCK,
            ADCLockCommand.LOCK,
            self._id_,
        )

    async def async_unlock(self):
        """Send unlock command."""
        await self._send_action_callback(
            ADCDeviceType.LOCK,
            ADCLockCommand.UNLOCK,
            self._id_,
        )


class ADCSensor(ADCBaseElement):
    """Represent Alarm.com system element."""

    class DeviceState(Enum):
        """Enum of sensor states."""

        UNKNOWN = 0
        CLOSED = 1
        OPEN = 2
        IDLE = 3
        ACTIVE = 4
        DRY = 5
        WET = 6

    @property
    def device_subtype(self) -> None or str:
        """Return normalized device subtype constant. E.g.: contact, glass break, etc."""
        try:
            return ADCSensorSubtype(self._attribs_raw.get("deviceType"))
        except ValueError:
            return None


class ADCGarageDoor(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com system element."""

    class DeviceState(Enum):
        """Enum of garage door states."""

        TRANSITIONING = 0
        OPEN = 1
        CLOSED = 2

    async def async_open(self):
        """Send unlock command."""
        await self._send_action_callback(
            ADCDeviceType.GARAGE_DOOR,
            ADCGarageDoorCommand.OPEN,
            self._id_,
        )

    async def async_close(self):
        """Send unlock command."""
        await self._send_action_callback(
            ADCDeviceType.GARAGE_DOOR,
            ADCGarageDoorCommand.CLOSE,
            self._id_,
        )
