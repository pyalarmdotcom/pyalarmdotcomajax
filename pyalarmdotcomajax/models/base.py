"""Alarm.com models."""

from __future__ import annotations

import logging
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Generic, TypeVar

from pyalarmdotcomajax.models.jsonapi import JsonApiBaseElement, Resource
from pyalarmdotcomajax.util import get_related_entity_id_by_key

log = logging.getLogger(__name__)


class ResourceType(StrEnum):
    """Type of resource."""

    # Devices
    CAMERA = "video/camera"
    GARAGE_DOOR = "devices/garage-door"
    GATE = "devices/gate"
    LIGHT = "devices/light"
    LOCK = "devices/lock"
    PARTITION = "devices/partition"
    SENSOR = "devices/sensor"
    SYSTEM = "systems/system"
    THERMOSTAT = "devices/thermostat"
    WATER_SENSOR = "devices/water-sensor"
    SWITCH = "devices/switch"

    IMAGE_SENSOR = "image-sensor/image-sensor"
    IMAGE_SENSOR_IMAGE = "image-sensor/image-sensor-image"

    # Meta
    AVAILABLE_SYSTEM = "systems/availableSystemItem"
    IDENTITY = "identity"
    PROFILE = "profile/profile"
    TWO_FACTOR = "twoFactorAuthentication/twoFactorAuthentication"
    TROUBLE_CONDITION = "troubleConditions/trouble-condition"
    DEVICE_CATALOG = "settings/manage-devices/device-catalog"

    UNKNOWN = "unknown"

    # UNSUPPORTED
    # ACCESS_CONTROL = "devices/access-control-access-point-device"
    # CAMERA_SD = "video/sd-card-camera"
    # CAR_MONITOR = "devices/car-monitor"
    # COMMERCIAL_TEMP = "devices/commercial-temperature-sensor"
    # GEO_DEVICE = "geolocation/geo-device"
    # IQ_ROUTER = "devices/iq-router"
    # REMOTE_TEMP = "devices/remote-temperature-sensor"
    # SCENE = "automation/scene"
    # SHADE = "devices/shade"
    # SMART_CHIME = "devices/smart-chime-device"
    # SUMP_PUMP = "devices/sump-pump"
    # VALVE_SWITCH = "valve-switch"
    # WATER_METER = "devices/water-meter"
    # WATER_VALVE = "devices/water-valve"
    # X10_LIGHT = "devices/x10-light"

    @classmethod
    def _missing_(cls: type, value: object) -> ResourceType:
        """Set default enum member if an unknown value is provided."""
        return ResourceType.UNKNOWN


# class DeviceType(StrEnum):
#     """Device type ids as returned by the ADC API."""

#     CAMERA = "cameras"
#     GARAGE_DOOR = "garageDoors"
#     GATE = "gates"
#     IMAGE_SENSOR = "imageSensors"
#     LIGHT = "lights"
#     LOCK = "locks"
#     PARTITION = "partitions"
#     SCENE = "scenes"
#     SENSOR = "sensors"
#     SYSTEM = "systems"
#     THERMOSTAT = "thermostats"
#     WATER_SENSOR = "waterSensors"
#     ACCESS_CONTROL = "accessControlAccessPointDevices"
#     CAMERA_SD = "sdCardCameras"
#     CAR_MONITOR = "carMonitors"
#     COMMERCIAL_TEMP = "commercialTemperatureSensors"
#     GEO_DEVICE = "geoDevices"
#     IQ_ROUTER = "iqRouters"
#     REMOTE_TEMP = "remoteTemperatureSensors"
#     SHADE = "shades"
#     SMART_CHIME = "smartChimeDevices"
#     SUMP_PUMP = "sumpPumps"
#     SWITCH = "switches"
#     VALVE_SWITCH = "valveSwitches"
#     WATER_METER = "waterMeters"
#     WATER_VALVE = "waterValves"
#     X10_LIGHT = "x10Lights"


#
# RESOURCES
#


@dataclass
class AdcResourceAttributes(ABC, JsonApiBaseElement):
    """Represents an Alarm.com resource."""

    pass


@dataclass
class AdcNamedDeviceAttributes(AdcResourceAttributes, ABC):
    """Represents an Alarm.com resource."""

    description: str = field(metadata={"description": "Device name"})


class AdcResourceSubtype(Enum):
    """Represents Alarm.com resource subtypes."""

    pass


AdcResourceAttributesT = TypeVar("AdcResourceAttributesT", bound=AdcResourceAttributes)
AdcNamedDeviceAttributesT = TypeVar("AdcNamedDeviceAttributesT", bound=AdcNamedDeviceAttributes)
AdcResourceSubtypesT = TypeVar("AdcResourceSubtypesT", bound=AdcResourceSubtype)


@dataclass
class AdcResource(Generic[AdcResourceAttributesT]):
    """
    Base class for all Alarm.com resource (device, identity, etc.).

    Accepts a JSON:API resource object. Casts dict of attributes into a dataclass.
    """

    api_resource: Resource = field(repr=False)

    resource_type: ResourceType = field(init=False)
    attributes_type: type[AdcResourceAttributesT] = field(init=False, repr=False)

    id: str = field(init=False)
    attributes: AdcResourceAttributesT = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the resource."""

        self.id = self.api_resource.id
        self.attributes: AdcResourceAttributesT = self.attributes_type.from_dict(self.api_resource.attributes)


@dataclass
class AdcDeviceResource(AdcResource[AdcNamedDeviceAttributesT]):
    """Base class for Alarm.com device resource."""

    # Mapping of model IDs to device manufacturer / model for device type.
    # deviceModelId: {"manufacturer": str, "model": str}
    resource_models: dict[int, dict[str, str]] = field(init=False, repr=False)

    attributes: AdcNamedDeviceAttributesT = field(init=False)

    system_id: str | None = field(init=False)
    model: str | None = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the resource."""

        super().__post_init__()

        self.system_id = get_related_entity_id_by_key(self.api_resource, "system")

        # Set device model
        self.model = None
        if hasattr(self, "resource_models"):
            if hasattr(self.attributes, "device_model") and getattr(self.attributes, "device_model"):
                self.model = str(getattr(self.attributes, "device_model"))
            elif hasattr(self.attributes, "device_model_id"):
                self.model = self.resource_models.get(getattr(self.attributes, "device_model_id"), {}).get("model")

        # self.extension_attributes: list[ExtensionAttributes] = []

    @property
    def name(self) -> str:
        """Name of the device."""

        return self.attributes.description


@dataclass
class AdcSubtypedResource(
    Generic[AdcResourceSubtypesT, AdcNamedDeviceAttributesT], AdcDeviceResource[AdcNamedDeviceAttributesT]
):
    """Base class for an Alarm.com device that uses subtypes."""

    resource_subtypes: type[AdcResourceSubtypesT] | None = field(default=None)
    subtype: AdcResourceSubtypesT | None = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the resource."""

        super().__post_init__()

        self.subtype = (
            self.resource_subtypes(self.attributes.device_type)
            if self.resource_subtypes and hasattr(self.attributes, "device_type")
            else None
        )


DeviceState = TypeVar("DeviceState", bound=Enum)


class BaseStatefulDeviceState(Enum):
    """Base device states."""

    LOADING_STATE = -1


@dataclass(kw_only=True)
class BaseStatefulDeviceAttributes(Generic[DeviceState], AdcNamedDeviceAttributes):
    """Base attributes for an alarm.com device."""

    # fmt: off
    # description: str = field(metadata={"description": "Device name"})
    battery_level_null: int | None = field(metadata={"description": "The current device battery level with null as the default value."})
    critical_battery: bool = field(metadata={"description": "Whether the device has a critical battery status."})
    low_battery: bool = field(metadata={"description": "Whether the device has a low battery status."})
    can_be_saved: bool = field(metadata={"description": "Does the logged in context have write permissions for this device?"})
    can_confirm_state_change: bool = field(metadata={"description": "Can the device confirm that its state changed?"})
    can_receive_commands: bool = field(metadata={"description": "Does this device support commands being sent to it?"})
    desired_state: BaseStatefulDeviceState | DeviceState | None = field(metadata={"description": "The desired device state."}, default=None)
    has_permission_to_change_state: bool = field(metadata={"description": "Can the logged in login change the state of this device?"})
    remote_commands_enabled: bool = field(metadata={"description": "Can the device status be changed remotely via app or web?"})
    state: BaseStatefulDeviceState | DeviceState = field(metadata={"description": "The current device state."})

    # animation_state: str = field(metadata={"description": "The model animation state."})
    # can_change_description: bool = field(metadata={"description": "Can the device description be changed?"})
    # device_icon: int = field(metadata={"description": "The icon to present the device."})
    # display_date: str = field(metadata={"description": "Returns the display string for the current stateInfo value."})
    # state_info: dict = field(metadata={"description": "ID for StateInfo object containing extended state information."})
    # state_subtext: str = field(metadata={"description": "The model state subtext for home cards."})
    # fmt: on

    @property
    def can_change_state(self) -> bool:
        """Whether the logged in user can change this device's state."""

        return self.has_permission_to_change_state and self.remote_commands_enabled

    @property
    def is_interactive(self) -> bool:
        """Whether the device is ready to be interacted with."""

        return self.can_change_state and self.state != BaseStatefulDeviceState.LOADING_STATE

    @property
    def is_refreshing_state(self) -> bool:
        """Whether the device is in the refreshing state."""

        return (self.state == BaseStatefulDeviceState.LOADING_STATE) or (self.state != self.desired_state)


#
# BASE MANAGED DEVICE
#


@dataclass(kw_only=True)
class BaseManagedDeviceAttributes(
    BaseStatefulDeviceAttributes[DeviceState],
    Generic[DeviceState],
):
    """Base attributes for an alarm.com managed device."""

    # fmt: off
    has_state: bool  # Does this device have a state?
    is_malfunctioning: bool  # Is the device currently set to a malfunction state.
    mac_address: str  # The mac address for the device, if available.
    manufacturer: str  # The manufacturer of the device.
    device_model: str | None = field(metadata={"description": "The device model."}, default=None)
    device_model_id: int | None = field(metadata={"description": "The device model id."}, default=None)

    # addDeviceResource: int  # The add device resource of the device.
    # associatedCameraDeviceIds: dict  # { device_id: device_name } for all associated cameras.
    # canAccessAppSettings: bool  # Can the app settings be accessed?
    # canAccessTroubleshootingWizard: bool  # Can the troubleshooting wizard be accessed?
    # canAccessWebSettings: bool  # Can the web settings be accessed?
    # canBeAssociatedToVideoDevice: bool  # Whether the device type can be associated to video devices.
    # canBeDeleted: bool  # Can the device be deleted?
    # canBeRenamed: bool  # Can the device be renamed?
    # isAssignedToCareReceiver: bool  # Is this mobile device assigned to a care receiver?
    # isOAuth: bool  # Is the device an OAuth device?
    # isZWave: bool  # Is the device a ZWave device.
    # managedDeviceType: int  # The type of device.
    # supportsCommandClassBasic: bool  # Does the Z-Wave device support CC Basic.
    # troubleshootingWizard # The route where the user can edit the troubleshooting wizard.
    # webSettings: int # The route where the user can edit the device settings on the web.
    # fmt: on
