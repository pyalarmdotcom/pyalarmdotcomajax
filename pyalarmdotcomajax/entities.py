"""Defines pyalarmdotcomajax components."""
from __future__ import annotations

from collections.abc import Callable
from enum import Enum
import logging
from typing import Protocol

from .const import ADCDeviceType
from .const import ADCGarageDoorCommand
from .const import ADCImageSensorCommand
from .const import ADCLightCommand
from .const import ADCLockCommand
from .const import ADCPartitionCommand
from .const import ADCRelationshipType
from .const import ADCSensorSubtype
from .const import ADCTroubleCondition
from .const import ElementSpecificData
from .const import ImageData

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

    @property
    def read_only(self) -> bool | None:
        """Return whether logged in user has permission to peek in."""
        return (
            not result
            if isinstance(
                (result := self._attribs_raw.get("hasPermissionToChangeState")),
                bool,
            )
            else None
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
    def state(self) -> DeviceState | None:
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

    @property
    def debug_data(self) -> dict:
        """Return data that is helpful for debugging."""
        return self._attribs_raw

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

    @property
    def read_only(self) -> None:
        """Non-actionable object."""
        return


class ADCPartition(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com partition element."""

    class DeviceState(Enum):
        """Enum of arming states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ArmingState.js

        UNKNOWN = 0
        DISARMED = 1
        ARMED_STAY = 2
        ARMED_AWAY = 3
        ARMED_NIGHT = 4

    @property
    def uncleared_issues(self) -> bool | None:
        """Return whether user needs to clear device state from alarm or device malfunction."""
        return self._attribs_raw.get("needsClearIssuesPrompt", None)

    async def _async_arm(
        self,
        arm_type: ADCPartitionCommand,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
        night_arming: bool = False,
    ) -> None:
        """Arm alarm system."""

        if arm_type == ADCPartitionCommand.DISARM:
            log.error("Invalid arm type.")
            return

        msg_body = {
            "forceBypass": force_bypass,
            "noEntryDelay": no_entry_delay,
            "silentArming": silent_arming,
            "nightArming": night_arming,
        }

        await self._send_action_callback(
            device_type=ADCDeviceType.PARTITION,
            event=arm_type,
            device_id=self.id_,
            msg_body=msg_body,
        )

    async def async_arm_stay(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""
        await self._async_arm(
            arm_type=ADCPartitionCommand.ARM_STAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
        )

    async def async_arm_away(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""
        await self._async_arm(
            arm_type=ADCPartitionCommand.ARM_AWAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
        )

    async def async_arm_night(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""
        await self._async_arm(
            arm_type=ADCPartitionCommand.ARM_STAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=True,
        )

    async def async_disarm(
        self,
    ) -> None:
        """Disarm alarm system."""

        await self._send_action_callback(
            device_type=ADCDeviceType.PARTITION,
            event=ADCPartitionCommand.DISARM,
            device_id=self.id_,
        )


class ADCLock(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com sensor element."""

    class DeviceState(Enum):
        """Enum of lock states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LockStatus.js

        UNKNOWN = 0
        LOCKED = 1
        UNLOCKED = 2

    async def async_lock(self) -> None:
        """Send lock command."""

        await self._send_action_callback(
            device_type=ADCDeviceType.LOCK,
            event=ADCLockCommand.LOCK,
            device_id=self.id_,
        )

    async def async_unlock(self) -> None:
        """Send unlock command."""

        await self._send_action_callback(
            device_type=ADCDeviceType.LOCK,
            event=ADCLockCommand.UNLOCK,
            device_id=self.id_,
        )


class ADCLight(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com light element."""

    class DeviceState(Enum):
        """Enum of light states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LightStatus.js

        OFFLINE = 0
        NOSTATE = 1
        ON = 2
        OFF = 3
        LEVELCHANGE = 4

    @property
    def available(self) -> bool:
        """Return whether the light can be manipulated."""
        return (
            self._attribs_raw.get("canReceiveCommands", False)
            and self._attribs_raw.get("remoteCommandsEnabled", False)
            and self._attribs_raw.get("hasPermissionToChangeState", False)
            and self.state
            in [self.DeviceState.ON, self.DeviceState.OFF, self.DeviceState.LEVELCHANGE]  # type: ignore
        )

    @property
    def brightness(self) -> int | None:
        """Return light's brightness."""
        if not self._attribs_raw.get("isDimmer", False):
            return None

        return self._attribs_raw.get("lightLevel", 0)

    @property
    def supports_state_tracking(self) -> bool | None:
        """Return whether the light reports its current state."""

        return self._attribs_raw.get("stateTrackingEnabled")

    async def async_turn_on(self, brightness: int | None = None) -> None:
        """Send turn on command with optional brightness."""

        msg_body: dict | None = None
        if brightness:
            msg_body = {}
            msg_body["dimmerLevel"] = brightness

        await self._send_action_callback(
            device_type=ADCDeviceType.LIGHT,
            event=ADCLightCommand.ON,
            device_id=self.id_,
            msg_body=msg_body,
        )

    async def async_turn_off(self) -> None:
        """Send turn off command."""

        await self._send_action_callback(
            device_type=ADCDeviceType.LIGHT,
            event=ADCLightCommand.OFF,
            device_id=self.id_,
        )


class ADCImageSensor(ADCBaseElement):
    """Represent Alarm.com image sensor element."""

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None

    @property
    def images(self) -> list[ImageData] | None:
        """Get a list of images taken by the image sensor."""

        if (
            self._element_specific_data is not None
            and self._element_specific_data.get("images") is not None
        ):
            return self._element_specific_data.get("images")

        return None

    async def async_peek_in(self) -> None:
        """Send peek in command to take photo."""

        await self._send_action_callback(
            device_type=ADCDeviceType.IMAGE_SENSOR,
            event=ADCImageSensorCommand.PEEK_IN,
            device_id=self.id_,
        )


class ADCSensor(ADCBaseElement):
    """Represent Alarm.com system element."""

    class DeviceState(Enum):
        """Enum of sensor states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/SensorStatus.js

        UNKNOWN = 0
        CLOSED = 1
        OPEN = 2
        IDLE = 3
        ACTIVE = 4
        DRY = 5
        WET = 6

        # Below not currently supported.
        # FULL = 7
        # LOW = 8
        # OPENED_CLOSED = 9
        # ISSUE = 10
        # OK = 11

    @property
    def device_subtype(self) -> ADCSensorSubtype | None:
        """Return normalized device subtype constant. E.g.: contact, glass break, etc."""
        try:
            return ADCSensorSubtype(self._attribs_raw["deviceType"])
        except ValueError:
            return None

    @property
    def read_only(self) -> None:
        """Non-actionable object."""
        return


class ADCGarageDoor(DesiredStateMixin, ADCBaseElement):
    """Represent Alarm.com garage door element."""

    class DeviceState(Enum):
        """Enum of garage door states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/GarageDoorStatus.js

        UNKNOWN = 0
        OPEN = 1
        CLOSED = 2

    async def async_open(self) -> None:
        """Send open command."""

        await self._send_action_callback(
            device_type=ADCDeviceType.GARAGE_DOOR,
            event=ADCGarageDoorCommand.OPEN,
            device_id=self.id_,
        )

    async def async_close(self) -> None:
        """Send close command."""

        await self._send_action_callback(
            device_type=ADCDeviceType.GARAGE_DOOR,
            event=ADCGarageDoorCommand.CLOSE,
            device_id=self.id_,
        )
