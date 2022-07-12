"""Representations of devices."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from enum import IntEnum
import logging
from typing import Any
from typing import final
from typing import Protocol
from typing import TypedDict

import aiohttp
from dateutil import parser
from pyalarmdotcomajax.errors import InvalidConfigurationOption
from pyalarmdotcomajax.errors import UnexpectedDataStructure
from pyalarmdotcomajax.extensions import CameraSkybellControllerExtension
from pyalarmdotcomajax.extensions import ConfigurationOption
from pyalarmdotcomajax.helpers import ExtendedEnumMixin

log = logging.getLogger(__name__)


class TroubleCondition(TypedDict):
    """Alarm.com alert / trouble condition."""

    message_id: str
    title: str
    body: str
    device_id: str


class DeviceType(ExtendedEnumMixin):
    """Enum of devices using ADC ids."""

    # Supported
    GARAGE_DOOR = "garageDoors"
    IMAGE_SENSOR = "imageSensors"
    LIGHT = "lights"
    LOCK = "locks"
    PARTITION = "partitions"
    SENSOR = "sensors"
    SYSTEM = "systems"
    THERMOSTAT = "thermostats"

    # Unsupported
    ACCESS_CONTROL = "accessControlAccessPointDevices"
    CAMERA = "cameras"
    CAMERA_SD = "sdCardCameras"
    CAR_MONITOR = "carMonitors"
    COMMERCIAL_TEMP = "commercialTemperatureSensors"
    # CONFIGURATION = "configuration"
    # FENCE = "fences"
    GATE = "gates"
    GEO_DEVICE = "geoDevices"
    IQ_ROUTER = "iqRouters"
    REMOTE_TEMP = "remoteTemperatureSensors"
    SCENE = "scenes"
    SHADE = "shades"
    SMART_CHIME = "smartChimeDevices"
    SUMP_PUMP = "sumpPumps"
    SWITCH = "switches"
    VALVE_SWITCH = "valveSwitches"
    WATER_METER = "waterMeters"
    WATER_SENSOR = "waterSensors"
    WATER_VALVE = "waterValves"
    X10_LIGHT = "x10Lights"


DEVICE_URLS: dict = {
    "supported": {
        DeviceType.CAMERA: {
            "relationshipId": "video/camera",
            "endpoint": "{}web/api/video/cameras/{}",
        },
        DeviceType.GARAGE_DOOR: {
            "relationshipId": "devices/garage-door",
            "endpoint": "{}web/api/devices/garageDoors/{}",
        },
        DeviceType.IMAGE_SENSOR: {
            "relationshipId": "image-sensor/image-sensor",
            "endpoint": "{}web/api/imageSensor/imageSensors/{}",
            "additional_endpoints": {
                "recent_images": (
                    "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"
                )
            },
        },
        DeviceType.LIGHT: {
            "relationshipId": "devices/light",
            "endpoint": "{}web/api/devices/lights/{}",
        },
        DeviceType.LOCK: {
            "relationshipId": "devices/lock",
            "endpoint": "{}web/api/devices/locks/{}",
        },
        DeviceType.PARTITION: {
            "relationshipId": "devices/partition",
            "endpoint": "{}web/api/devices/partitions/{}",
        },
        DeviceType.SENSOR: {
            "relationshipId": "devices/sensor",
            "endpoint": "{}web/api/devices/sensors/{}",
        },
        DeviceType.SYSTEM: {
            "relationshipId": "systems/system",
            "endpoint": "{}web/api/systems/systems/{}",
        },
        DeviceType.THERMOSTAT: {
            "relationshipId": "devices/thermostat",
            "endpoint": "{}web/api/devices/thermostats/{}",
        },
    },
    "unsupported": {
        DeviceType.ACCESS_CONTROL: {
            "relationshipId": "devices/access-control-access-point-device",
            "endpoint": "{}web/api/devices/accessControlAccessPointDevices/{}",
        },
        DeviceType.CAMERA_SD: {
            "relationshipId": "video/sd-card-camera",
            "endpoint": "{}web/api/video/sdCardCameras/{}",
        },
        DeviceType.CAR_MONITOR: {
            "relationshipId": "devices/car-monitor",
            "endpoint": "{}web/api/devices/carMonitors{}",
        },
        DeviceType.COMMERCIAL_TEMP: {
            "relationshipId": "devices/commercial-temperature-sensor",
            "endpoint": "{}web/api/devices/commercialTemperatureSensors/{}",
        },
        # DeviceType.CONFIGURATION: {
        #     "relationshipId": "configuration",
        #     "endpoint": "{}web/api/systems/configurations/{}",
        # },
        # DeviceType.FENCE: {
        #     "relationshipId": "",
        #     "endpoint": "{}web/api/geolocation/fences/{}",
        # },
        DeviceType.GATE: {
            "relationshipId": "devices/gate",
            "endpoint": "{}web/api/devices/gates/{}",
        },
        DeviceType.GEO_DEVICE: {
            "relationshipId": "geolocation/geo-device",
            "endpoint": "{}web/api/geolocation/geoDevices/{}",
        },
        DeviceType.IQ_ROUTER: {
            "relationshipId": "devices/iq-router",
            "endpoint": "{}web/api/devices/iqRouters/{}",
        },
        DeviceType.REMOTE_TEMP: {
            "relationshipId": "devices/remote-temperature-sensor",
            "endpoint": "{}web/api/devices/remoteTemperatureSensors/{}",
        },
        DeviceType.SCENE: {
            "relationshipId": "automation/scene",
            "endpoint": "{}web/api/automation/scenes/{}",
        },
        DeviceType.SHADE: {
            "relationshipId": "devices/shade",
            "endpoint": "{}web/api/devices/shades/{}",
        },
        DeviceType.SMART_CHIME: {
            "relationshipId": "devices/smart-chime-device",
            "endpoint": "{}web/api/devices/smartChimeDevices/{}",
        },
        DeviceType.SUMP_PUMP: {
            "relationshipId": "devices/sump-pump",
            "endpoint": "{}web/api/devices/sumpPumps/{}",
        },
        DeviceType.SWITCH: {
            "relationshipId": "devices/switch",
            "endpoint": "{}web/api/devices/switches/{}",
        },
        DeviceType.VALVE_SWITCH: {
            "relationshipId": "valve-switch",
            "endpoint": "{}web/api/devices/valveSwitches/{}",
        },
        DeviceType.WATER_METER: {
            "relationshipId": "devices/water-meter",
            "endpoint": "{}web/api/devices/waterMeters/{}",
        },
        DeviceType.WATER_SENSOR: {
            "relationshipId": "devices/water-sensor",
            "endpoint": "{}web/api/devices/waterSensors/{}",
        },
        DeviceType.WATER_VALVE: {
            "relationshipId": "devices/water-valve",
            "endpoint": "{}web/api/devices/waterValves/{}",
        },
        DeviceType.X10_LIGHT: {
            "relationshipId": "devices/x10light",
            "endpoint": "{}web/api/devices/x10Lights/{}",
        },
    },
}


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
        except (ValueError, TypeError):
            return None
        else:
            return state


class ElementSpecificData(TypedDict, total=False):
    """Hold entity-type-specific metadata."""

    raw_recent_images: set[dict]


class BaseDevice:
    """Contains properties shared by all ADC devices."""

    def __init__(
        self,
        id_: str,
        send_action_callback: Callable,
        config_change_callback: Callable | None,
        subordinates: list,
        raw_device_data: dict,
        element_specific_data: ElementSpecificData | None = None,
        trouble_conditions: list | None = None,
        partition_id: str | None = None,
        settings: dict | None = None,  # slug: ConfigurationOption
    ) -> None:
        """Initialize base element class."""

        self._id_: str = id_
        self._family_raw: str | None = raw_device_data.get("type")
        self._attribs_raw: dict = raw_device_data.get("attributes", {})
        self._element_specific_data: ElementSpecificData = (
            element_specific_data if element_specific_data else {}
        )
        self._send_action_callback: Callable = send_action_callback
        self._config_change_callback: Callable | None = config_change_callback
        self._subordinates: list = subordinates
        self._settings: dict = settings if settings else {}

        self.trouble_conditions: list[TroubleCondition] = (
            trouble_conditions if trouble_conditions else []
        )

        self._system_id: str | None = (
            raw_device_data.get("relationships", {})
            .get("system", {})
            .get("data", {})
            .get("id")
        )
        self._partition_id: str | None = partition_id

        self.process_element_specific_data()

        log.debug("Initialized %s %s", self._family_raw, self.name)

    #
    # Casting Functions
    #
    # Functions used for pulling data from _raw_attribs in standardized format.
    @final
    def _get_int(self, key: str) -> int | None:
        """Cast raw value to int. Satisfies mypy."""

        try:
            return int(self._attribs_raw.get(key))  # type: ignore
        except (ValueError, TypeError):
            return None

    def _get_str(self, key: str) -> str | None:
        """Cast raw value to str. Satisfies mypy."""

        try:
            return str(self._attribs_raw.get(key))
        except (ValueError, TypeError):
            return None

    def _get_bool(self, key: str) -> bool | None:
        """Cast raw value to bool. Satisfies mypy."""

        if str(self._attribs_raw.get(key)).lower() == "true":
            return True

        if str(self._attribs_raw.get(key)).lower() == "false":
            return False

        return None

    def _get_list(self, key: str, value_type: type) -> list | None:
        """Cast raw value to bool. Satisfies mypy."""

        try:
            duration_list: list = list(self._attribs_raw.get(key))  # type: ignore
            for duration in duration_list:
                value_type(duration)
            return duration_list
        except (ValueError, TypeError):
            pass

        return None

    def _get_special(self, key: str, value_type: type) -> Any | None:
        """Cast raw value to bool. Satisfies mypy."""

        try:
            return value_type(self._attribs_raw.get(key))
        except (ValueError, TypeError):
            pass

        return None

    #
    # Properties
    #

    @property
    def read_only(self) -> bool | None:
        """Return whether logged in user has permission to change state."""
        return (
            not result
            if isinstance(
                (result := self._attribs_raw.get("hasPermissionToChangeState")),
                bool,
            )
            else None
        )

    @property
    def id_(self) -> str:
        """Return device ID."""
        return self._id_

    @property
    def name(self) -> None | str:
        """Return user-assigned device name."""
        return self._attribs_raw.get("description", None)

    @property
    def has_state(self) -> bool:
        """Return whether entity reports state."""
        return self._attribs_raw.get("hasState", False)

    @property
    def state(self) -> Enum | None:
        """Return state."""

        try:
            state = self.DeviceState(self._attribs_raw.get("state"))
        except ValueError:
            return None
        else:
            return state

    @property
    def settings(self) -> dict:
        """Return user-changable settings."""

        return {
            config_option.slug: config_option
            for config_option in self._settings.values()
            if isinstance(config_option, ConfigurationOption)
            and config_option.user_configurable
        }

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
        return self._system_id

    @property
    def partition_id(self) -> str | None:
        """Return ID of device's parent partition."""
        return self._partition_id

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
    def model_text(self) -> str | None:
        """Return device model as reported by ADC."""
        return (
            reported_model
            if (reported_model := self._attribs_raw.get("deviceModel"))
            else self.DEVICE_MODELS.get(self._attribs_raw.get("deviceModelId"))
        )

    @property
    def manufacturer(self) -> str | None:
        """Return device model as reported by ADC."""
        return self._attribs_raw.get("manufacturer")

    @property
    def debug_data(self) -> dict:
        """Return data that is helpful for debugging."""
        return self._attribs_raw

    @property
    def device_subtype(self) -> Enum | None:
        """Return normalized device subtype const. E.g.: contact, glass break, etc."""
        try:
            return self.Subtype(self._attribs_raw["deviceType"])
        except (ValueError, KeyError):
            return None

    # #
    # PLACEHOLDERS
    # #

    # All subclasses will have above functions. Only some will have the below and must be implemented as overloads.
    # Methods below are included here to silence mypy errors.

    class DeviceState(Enum):
        """Hold device state values. To be overridden by children."""

    class Command(Enum):
        """Hold device commands. To be overridden by children."""

    class Subtype(Enum):
        """Hold device subtypes. To be overridden by children."""

    # deviceModelId: {"manufacturer": str, "model": str}
    DEVICE_MODELS: dict = {}

    @property
    def desired_state(self) -> Enum | None:
        """Return state. To be overridden by children."""

    def process_element_specific_data(self) -> None:  # pylint: disable=no-self-use
        """Process element specific data. To be overridden by children."""

        return None

    async def async_change_setting(self, slug: str, new_value: Any) -> None:
        """Update specified configuration setting via extension."""

        if not self._config_change_callback:
            log.error(
                "async_change_setting called for %s, which does not have a"
                " config_change_callback set.",
                self.name,
            )
            return

        config_option: ConfigurationOption | None = self.settings.get(slug)
        extension: type[CameraSkybellControllerExtension] | None = (
            config_option.extension if config_option else None
        )

        if not extension:
            raise InvalidConfigurationOption

        log.debug(
            "BaseDevice -> async_change_setting: Calling change setting function for %s"
            " %s (%s) via extension %s.",
            type(self).__name__,
            self.name,
            self.id_,
            extension,
        )

        try:
            updated_option = await self._config_change_callback(
                camera_name=self.name, slug=slug, new_value=new_value
            )
        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
            asyncio.exceptions.CancelledError,
        ) as err:
            raise err
        except UnexpectedDataStructure as err:
            raise err

        self._settings["slug"] = updated_option


class Camera(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com camera element."""

    # Cameras do not have a state.

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None


class GarageDoor(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com garage door element."""

    class DeviceState(Enum):
        """Enum of garage door states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/GarageDoorStatus.js

        UNKNOWN = 0
        OPEN = 1
        CLOSED = 2

    class Command(Enum):
        """Commands for ADC garage doors."""

        OPEN = "open"
        CLOSE = "close"

    async def async_open(self) -> None:
        """Send open command."""

        await self._send_action_callback(
            device_type=DeviceType.GARAGE_DOOR,
            event=self.Command.OPEN,
            device_id=self.id_,
        )

    async def async_close(self) -> None:
        """Send close command."""

        await self._send_action_callback(
            device_type=DeviceType.GARAGE_DOOR,
            event=self.Command.CLOSE,
            device_id=self.id_,
        )


class ImageSensorImage(TypedDict):
    """Holds metadata for image sensor images."""

    id_: str
    image_b64: str
    image_src: str
    description: str
    timestamp: datetime


class ImageSensor(BaseDevice):
    """Represent Alarm.com image sensor element."""

    class Command(Enum):
        """Commands for ADC image sensors."""

        PEEK_IN = "doPeekInNow"

    _recent_images: list[ImageSensorImage] = []

    def process_element_specific_data(self) -> None:
        """Process recent images."""

        if not (
            raw_recent_images := self._element_specific_data.get("raw_recent_images")
        ):
            return

        for image in raw_recent_images:
            if (
                isinstance(image, dict)
                and str(
                    image.get("relationships", {})
                    .get("imageSensor", {})
                    .get("data", {})
                    .get("id")
                )
                == self.id_
            ):
                image_data: ImageSensorImage = {
                    "id_": image["id"],
                    "image_b64": image["attributes"]["image"],
                    "image_src": image["attributes"]["imageSrc"],
                    "description": image["attributes"]["description"],
                    "timestamp": parser.parse(image["attributes"]["timestamp"]),
                }
                self._recent_images.append(image_data)

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None

    @property
    def images(self) -> list[ImageSensorImage] | None:
        """Get a list of images taken by the image sensor."""

        return self._recent_images

    async def async_peek_in(self) -> None:
        """Send peek in command to take photo."""

        await self._send_action_callback(
            device_type=DeviceType.IMAGE_SENSOR,
            event=self.Command.PEEK_IN,
            device_id=self.id_,
        )


class Light(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com light element."""

    class DeviceState(Enum):
        """Enum of light states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LightStatus.js

        OFFLINE = 0
        NOSTATE = 1
        ON = 2
        OFF = 3
        LEVELCHANGE = 4

    class Command(Enum):
        """Commands for ADC lights."""

        ON = "turnOn"
        OFF = "turnOff"

    @property
    def available(self) -> bool:
        """Return whether the light can be manipulated."""
        return (
            self._attribs_raw.get("canReceiveCommands", False)
            and self._attribs_raw.get("remoteCommandsEnabled", False)
            and self._attribs_raw.get("hasPermissionToChangeState", False)
            and self.state
            in [self.DeviceState.ON, self.DeviceState.OFF, self.DeviceState.LEVELCHANGE]
        )

    @property
    def brightness(self) -> int | None:
        """Return light's brightness."""
        if not self._attribs_raw.get("isDimmer", False):
            return None

        if isinstance(level := self._attribs_raw.get("lightLevel", 0), int):
            return level

        return None

    @property
    def supports_state_tracking(self) -> bool | None:
        """Return whether the light reports its current state."""

        if isinstance(supports := self._attribs_raw.get("stateTrackingEnabled"), bool):
            return supports

        return None

    async def async_turn_on(self, brightness: int | None = None) -> None:
        """Send turn on command with optional brightness."""

        msg_body: dict | None = None
        if brightness:
            msg_body = {}
            msg_body["dimmerLevel"] = brightness

        await self._send_action_callback(
            device_type=DeviceType.LIGHT,
            event=self.Command.ON,
            device_id=self.id_,
            msg_body=msg_body,
        )

    async def async_turn_off(self) -> None:
        """Send turn off command."""

        await self._send_action_callback(
            device_type=DeviceType.LIGHT,
            event=self.Command.OFF,
            device_id=self.id_,
        )


class Lock(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com sensor element."""

    class DeviceState(Enum):
        """Enum of lock states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/LockStatus.js

        UNKNOWN = 0
        LOCKED = 1
        UNLOCKED = 2

    class Command(Enum):
        """Commands for ADC locks."""

        LOCK = "lock"
        UNLOCK = "unlock"

    async def async_lock(self) -> None:
        """Send lock command."""

        await self._send_action_callback(
            device_type=DeviceType.LOCK,
            event=self.Command.LOCK,
            device_id=self.id_,
        )

    async def async_unlock(self) -> None:
        """Send unlock command."""

        await self._send_action_callback(
            device_type=DeviceType.LOCK,
            event=self.Command.UNLOCK,
            device_id=self.id_,
        )


class Partition(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com partition element."""

    class DeviceState(Enum):
        """Enum of arming states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ArmingState.js

        UNKNOWN = 0
        DISARMED = 1
        ARMED_STAY = 2
        ARMED_AWAY = 3
        ARMED_NIGHT = 4

    class Command(Enum):
        """Commands for ADC partitions."""

        DISARM = "disarm"
        ARM_STAY = "armStay"
        ARM_AWAY = "armAway"

    @property
    def uncleared_issues(self) -> bool | None:
        """Return whether user needs to clear device state on alarm.com."""
        if isinstance(
            issues := self._attribs_raw.get("needsClearIssuesPrompt", None), bool
        ):
            return issues

        return None

    async def _async_arm(
        self,
        arm_type: Command,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
        night_arming: bool = False,
    ) -> None:
        """Arm alarm system."""

        if arm_type == self.Command.DISARM:
            log.error("Invalid arm type.")
            return

        msg_body = {
            "forceBypass": force_bypass,
            "noEntryDelay": no_entry_delay,
            "silentArming": silent_arming,
            "nightArming": night_arming,
        }

        await self._send_action_callback(
            device_type=DeviceType.PARTITION,
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

        log.debug("Calling arm stay.")

        await self._async_arm(
            arm_type=self.Command.ARM_STAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=False,
        )

    async def async_arm_away(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm away.")

        await self._async_arm(
            arm_type=self.Command.ARM_AWAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=False,
        )

    async def async_arm_night(
        self,
        force_bypass: bool = False,
        no_entry_delay: bool = False,
        silent_arming: bool = False,
    ) -> None:
        """Arm stay alarm."""

        log.debug("Calling arm night.")

        await self._async_arm(
            arm_type=self.Command.ARM_STAY,
            force_bypass=force_bypass,
            no_entry_delay=no_entry_delay,
            silent_arming=silent_arming,
            night_arming=True,
        )

    async def async_disarm(
        self,
    ) -> None:
        """Disarm alarm system."""

        log.debug("Calling disarm.")

        await self._send_action_callback(
            device_type=DeviceType.PARTITION,
            event=self.Command.DISARM,
            device_id=self.id_,
        )


class Sensor(BaseDevice):
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

    class Subtype(IntEnum):
        """Library of identified ADC device types."""

        CONTACT_SENSOR = 1
        MOTION_SENSOR = 2
        SMOKE_DETECTOR = 5
        FREEZE_SENSOR = 8
        CO_DETECTOR = 6
        PANIC_BUTTON = 9
        FIXED_PANIC = 10
        SIREN = 14
        GLASS_BREAK_DETECTOR = 19
        CONTACT_SHOCK_SENSOR = 52
        PANEL_MOTION_SENSOR = 89
        PANEL_GLASS_BREAK_DETECTOR = 83
        PANEL_IMAGE_SENSOR = 68
        MOBILE_PHONE = 69

    @property
    def read_only(self) -> None:
        """Non-actionable object."""
        return


class System(BaseDevice):
    """Represent Alarm.com system element."""

    @property
    def unit_id(self) -> str | None:
        """Return device ID."""
        if not (raw_id := self._attribs_raw.get("unitId")):
            return str(raw_id)

        return None

    @property
    def read_only(self) -> None:
        """Non-actionable object."""
        return

    @property
    def malfunction(self) -> bool | None:
        """Return whether device is malfunctioning."""
        return None


class Thermostat(DesiredStateMixin, BaseDevice):
    """Represent Alarm.com thermostat element."""

    # fan duration of 0 is indefinite. otherwise value == hours.
    # settable attributes: desiredRts (remote temp sensor), desiredLocalDisplayLockingMode,
    # In identity info, check localizeTempUnitsToCelsius.

    @dataclass
    class ThermostatAttributes:
        """Thermostat attributes."""

        # Base
        temp_average: int | None  # Temperature from thermostat and all remote sensors, averaged.
        temp_at_tstat: int | None  # Temperature at thermostat only.
        step_value: int | None
        # Fan
        support_fan_mode: bool | None
        support_fan_indefinite: bool | None
        support_fan_circulate_when_off: bool | None
        support_fan_durations: list[int] | None
        fan_mode: Thermostat.FanMode | None
        fan_duration: int | None
        # Temp
        support_heat: bool | None
        support_cool: bool | None
        support_auto: bool | None
        min_heat_setpoint: int | None
        max_heat_setpoint: int | None
        min_cool_setpoint: int | None
        max_cool_setpoint: int | None
        heat_setpoint: int | None
        cool_setpoint: int | None
        # Humidity
        support_humidity: bool | None
        humidity: int | None
        # Schedules
        support_schedules: bool | None
        support_schedules_smart: bool | None
        schedule_mode: Thermostat.ScheduleMode | None

    class DeviceState(Enum):
        """Enum of thermostat states."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatStatus.js

        UNKNOWN = 0
        OFF = 1
        HEAT = 2
        COOL = 3
        AUTO = 4
        AUX_HEAT = 5

    class FanMode(Enum):
        """Enum of thermostat fan modes."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatFanMode.js

        AUTO_LOW = 0
        ON_LOW = 1
        AUTO_HIGH = 2
        ON_HIGH = 3
        AUTO_MEDIUM = 4
        ON_MEDIUM = 5
        CIRCULATE = 6
        HUMIDITY = 7

    class LockMode(Enum):
        """Enum of thermostat lock modes."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatLock.js

        DISABLED = 0
        ENABLED = 1
        PARTIAL = 2

    class ScheduleMode(Enum):
        """Enum of thermostat programming modes."""

        # https://www.alarm.com/web/system/assets/customer-ember/enums/ThermostatProgrammingMode.js

        MANUAL = 0
        SCHEDULED = 1
        SMART_SCHEDULES = 2

    class SetpointType(Enum):
        """Enum of thermostat setpoint types."""

        FIXED = 0
        AWAY = 1
        HOME = 2
        SLEEP = 3

    class Command(Enum):
        """Commands for ADC lights."""

        SET_STATE = "setState"

    DEVICE_MODELS = {4293: {"manufacturer": "Honeywell", "model": "T6 Pro"}}

    @property
    def available(self) -> bool:
        """Return whether the light can be manipulated."""
        return (
            self._attribs_raw.get("canReceiveCommands", False)
            and self._attribs_raw.get("remoteCommandsEnabled", False)
            and self._attribs_raw.get("hasPermissionToChangeState", False)
            and self.state is not self.DeviceState.UNKNOWN
        )

    @property
    def attributes(self) -> ThermostatAttributes:
        """Return thermostat attributes."""

        return self.ThermostatAttributes(
            temp_average=self._get_int("forwardingAmbientTemp"),
            temp_at_tstat=self._get_int("ambientTemp"),
            step_value=self._get_int("setpointOffset"),
            support_fan_mode=self._get_bool("supportsFanMode"),
            support_fan_indefinite=self._get_bool("supportsCirculateFanModeWhenOff"),
            support_fan_circulate_when_off=self._get_bool(
                "support_fan_circulate_when_off"
            ),
            support_fan_durations=self._get_list("supportedFanDurations", int),
            fan_mode=self._get_special("supportedFanDurations", self.FanMode),
            fan_duration=self._get_int("fanDuration"),
            support_heat=self._get_bool("supportsHeatMode"),
            support_cool=self._get_bool("supportsCoolMode"),
            support_auto=self._get_bool("supportsAutoMode"),
            min_heat_setpoint=self._get_int("minHeatSetpoint"),
            min_cool_setpoint=self._get_int("minCoolSetpoint"),
            max_heat_setpoint=self._get_int("maxHeatSetpoint"),
            max_cool_setpoint=self._get_int("maxCoolSetpoint"),
            heat_setpoint=self._get_int("heatSetpoint"),
            cool_setpoint=self._get_int("coolSetpoint"),
            support_humidity=self._get_bool("supportsHumidity"),
            humidity=self._get_int("humidityLevel"),
            support_schedules=self._get_bool("supportsSchedules"),
            support_schedules_smart=self._get_bool("supportsSmartSchedules"),
            schedule_mode=self._get_special("scheduleMode", self.ScheduleMode),
        )

    async def async_set_attribute(
        self,
        state: DeviceState | None = None,
        fan: tuple[FanMode, int] | None = None,  # int = duration
        cool_setpoint: int | None = None,
        heat_setpoint: int | None = None,
        schedule_mode: ScheduleMode | None = None,
    ) -> None:
        """Send turn on command with optional brightness."""

        msg_body = {}

        # Make sure we're only being asked to set one attribute at a time.
        if (
            attrib_list := [state, fan, cool_setpoint, heat_setpoint, schedule_mode]
        ).count(None) < len(attrib_list):
            raise UnexpectedDataStructure

        # Build the request body.
        if state:
            msg_body = {"desiredState": state.value}
        elif fan:
            msg_body = {
                "desiredFanMode": self.FanMode(fan[0]).value,
                "desiredFanDuration": fan[1],
            }
        elif cool_setpoint:
            msg_body = {"desiredCoolSetpoint": cool_setpoint}
        elif heat_setpoint:
            msg_body = {"desiredHeatSetpoint": heat_setpoint}
        elif schedule_mode:
            msg_body = {"desiredScheduleMode": schedule_mode.value}

        # Send
        await self._send_action_callback(
            device_type=DeviceType.THERMOSTAT,
            event=self.Command.SET_STATE,
            device_id=self.id_,
            msg_body=msg_body,
        )
