"""Defines pyalarmdotcomajax components."""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import logging
from typing import Protocol

from .const import (
    ADCDeviceType,
    ADCGarageDoorCommand,
    ADCImageSensorCommand,
    ADCLockCommand,
    ADCPartitionCommand,
    ADCRelationshipType,
    ADCSensorSubtype,
    ADCTroubleCondition,
    ElementSpecificData,
    ImageData,
)

log = logging.getLogger(__name__)

#
# Mixins
#


class DesiredStateProtocol(Protocol):
    """Private variables for DesiredStateMixin."""

    _attribs_raw: dict
    desired_state: Enum | None
    has_state: bool
    state: Enum | None
    DeviceState: type[Enum]


class DesiredStateMixin:
    """Mixin decorator for entities with desired_state attribute."""

    @property
    def desired_state(self: DesiredStateProtocol) -> Enum | None:
        """Return state."""

        try:
            state: Enum = self.DeviceState(self._attribs_raw.get("desiredState"))
        except ValueError:
            return None
        else:
            return state


#
# ADC Core Elements
#


class ADCBaseElement:
    """Contains properties shared by all ADC devices."""

    def __init__(
        self,
        send_action_callback: Callable,
        id_: str,
        attribs_raw: dict,
        subordinates: list,
        parent_ids: dict | None = None,
        family_raw: str | None = None,
        element_specific_data: ElementSpecificData | None = None,
        trouble_conditions: list | None = None,
    ) -> None:
        """Initialize base element class."""
        self._id_: str = id_
        self._family_raw: str | None = family_raw
        self._attribs_raw: dict = attribs_raw
        self._element_specific_data: ElementSpecificData | None = element_specific_data
        self._parent_ids: dict | None = parent_ids
        self._send_action_callback: Callable = send_action_callback
        self._subordinates: list = subordinates
        self.trouble_conditions: list[ADCTroubleCondition] = (
            trouble_conditions if trouble_conditions else []
        )

        if parent_ids:
            self._system_id: str | None = parent_ids.get("system")
            self._partition_id: str | None = parent_ids.get("partition")
            self._parent_id_: str | None = parent_ids.get("parent_device")

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
    def name(self) -> None | str:
        """Return user-assigned device name."""
        return self._attribs_raw.get("description", None)

    @property
    def device_type(self) -> None | ADCRelationshipType:
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
    def state(self) -> str | bool | DeviceState | None:
        """Return state."""

        try:
            state = self.DeviceState(self._attribs_raw.get("state"))
        except ValueError:
            return None
        else:
            return state

    @property
    def battery_low(self) -> bool | None:
        """Return whether battery is low."""
        return self._attribs_raw.get("lowBattery")

    @property
    def battery_critical(self) -> bool | None:
        """Return whether battery is critically low."""
        return self._attribs_raw.get("criticalBattery")

    @property
    def system_id(self) -> str | None:
        """Return ID of device's parent system."""
        return self._parent_ids.get("system") if self._parent_ids is not None else None

    @property
    def partition_id(self) -> str | None:
        """Return ID of device's parent partition."""
        return (
            self._parent_ids.get("partition") if self._parent_ids is not None else None
        )

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return self._attribs_raw.get("isMalfunctioning", True) or self.state is None

    @property
    def mac_address(self) -> bool | None:
        """Return device MAC address."""
        return self._attribs_raw.get("macAddress")

    @property
    def raw_state_text(self) -> str | None:
        """Return state description as reported by ADC."""
        return self._attribs_raw.get("displayStateText")

    # def is_subordinate(self, device_id: str) -> bool:
    #     """Return whether submitted device is downstream from this device."""
    #     return [i_id for i_id in self._subordinates if i_id[0] == device_id]

    # #
    # PLACEHOLDERS
    # #

    # All subclasses will have above functions. Only some will have the below and must be implemented as overloads.
    # Methods below are included here to silence mypy errors.

    @property
    def desired_state(self) -> Enum | None:
        """Return state."""

    @property
    def device_subtype(self) -> ADCSensorSubtype | None:
        """Return normalized device subtype constant. E.g.: contact, glass break, etc."""


class ADCSystem(ADCBaseElement):
    """Represent Alarm.com system element."""

    @property
    def unit_id(self) -> str:
        """Return device ID."""
        return self._attribs_raw.get("unitId", None)

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None


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
    def uncleared_issues(self) -> bool | None:
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
    """Represent Alarm.com sensor element."""

    class DeviceState(Enum):
        """Enum of lock states."""

        FAILED = 0
        LOCKED = 1
        UNLOCKED = 2

    async def async_lock(self) -> None:
        """Send lock command."""
        await self._send_action_callback(
            ADCDeviceType.LOCK,
            ADCLockCommand.LOCK,
            self._id_,
        )

    async def async_unlock(self) -> None:
        """Send unlock command."""
        await self._send_action_callback(
            ADCDeviceType.LOCK,
            ADCLockCommand.UNLOCK,
            self._id_,
        )


class ADCImageSensor(ADCBaseElement):
    """Represent Alarm.com image sensor element."""

    async def async_peek_in(self) -> None:
        """Send peek in command."""
        await self._send_action_callback(
            ADCDeviceType.IMAGE_SENSOR,
            ADCImageSensorCommand.peekIn,
            self._id_,
        )

    @property
    def images(self) -> list[ImageData] | None:
        """Get a list of images taken by the image sensor."""

        if (
            self._element_specific_data is not None
            and self._element_specific_data.get("images") is not None
        ):
            return self._element_specific_data.get("images")

        return None


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
    def device_subtype(self) -> ADCSensorSubtype | None:
        """Return normalized device subtype constant. E.g.: contact, glass break, etc."""
        try:
            return ADCSensorSubtype(self._attribs_raw["deviceType"])
        except ValueError:
            return None


class ADCGarageDoor(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com garage door element."""

    class DeviceState(Enum):
        """Enum of garage door states."""

        OPEN = 1
        CLOSED = 2

    async def async_open(self) -> None:
        """Send unlock command."""
        await self._send_action_callback(
            ADCDeviceType.GARAGE_DOOR,
            ADCGarageDoorCommand.OPEN,
            self._id_,
        )

    async def async_close(self) -> None:
        """Send unlock command."""
        await self._send_action_callback(
            ADCDeviceType.GARAGE_DOOR,
            ADCGarageDoorCommand.CLOSE,
            self._id_,
        )
