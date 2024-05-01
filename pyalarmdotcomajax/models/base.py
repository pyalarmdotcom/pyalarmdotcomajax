"""Alarm.com models."""

import logging
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Generic, TypeVar

from mashumaro import field_options

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
    HISTORY_EVENT = "activity/history-event"

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
    def _missing_(cls: type, value: object) -> "ResourceType":
        """Set default enum member if an unknown value is provided."""
        return ResourceType.UNKNOWN


#
# RESOURCES
#


@dataclass
class AdcResourceAttributes(ABC, JsonApiBaseElement):
    """Represents an Alarm.com resource."""


@dataclass
class AdcNamedDeviceAttributes(AdcResourceAttributes, ABC):
    """Represents an Alarm.com resource."""

    description: str = field(metadata={"description": "Device name"})


class AdcResourceSubtype(Enum):
    """Represents Alarm.com resource subtypes."""


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
            if hasattr(self.attributes, "device_model") and self.attributes.device_model:
                self.model = str(self.attributes.device_model)
            elif hasattr(self.attributes, "device_model_id"):
                self.model = self.resource_models.get(self.attributes.device_model_id, {}).get("model")

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
    battery_level_pct: int | None = field(metadata=field_options(alias="battery_level_null")) # The current battery level of the device as a percentage with null as the default value.
    critical_battery: bool = field(metadata={"description": "Indicate whether the device has a critical battery status."})
    low_battery: bool = field(metadata={"description": "Indicate whether the device has a low battery status."})
    can_be_saved: bool = field(metadata={"description": "Whether the logged in context has write permissions for this device."})
    can_confirm_state_change: bool = field(metadata={"description": "Whether the device can confirm its state change."})
    can_receive_commands: bool = field(metadata={"description": "Whether device supports receiving commands."})
    desired_state: BaseStatefulDeviceState | DeviceState | None = field(metadata={"description": "Desired device state."}, default=None)
    has_permission_to_change_state: bool = field(metadata={"description": "Whether logged in user can change device state."})
    remote_commands_enabled: bool = field(metadata={"description": "Whether device can be changed remotely via app or web."})
    state: BaseStatefulDeviceState | DeviceState = field(metadata={"description": "Current device state."})
    # fmt: on

    @property
    def can_change_state(self) -> bool:
        """Whether the logged in user can change this device's state."""

        return self.has_permission_to_change_state and self.remote_commands_enabled

    @property
    def interactive(self) -> bool:
        """Whether the device is ready to be interacted with."""

        return self.can_change_state and self.state != BaseStatefulDeviceState.LOADING_STATE

    @property
    def refreshing_state(self) -> bool:
        """Whether the device is in the refreshing state."""

        return self.loading or (self.state != self.desired_state)

    @property
    def loading(self) -> bool:
        """
        Whether the device is loading.

        None means undetermined.
        """

        return self.state == BaseStatefulDeviceState.LOADING_STATE


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
    has_state: bool = field(metadata={"description": "Does this device have a state?"})
    is_malfunctioning: bool = field(metadata={"description": "Is the device currently set to a malfunction state."})
    mac_address: str = field(metadata={"description": "The mac address for the device, if available."})
    manufacturer: str = field(metadata={"description": "The manufacturer of the device."})
    device_model: str | None = field(metadata={"description": "The device model."}, default=None)
    device_model_id: int | None = field(metadata={"description": "The device model id."}, default=None)

    # associatedCameraDeviceIds: dict  # { device_id: device_name } for all associated cameras.
    # canAccessWebSettings: bool  # Can the web settings be accessed?
    # isOAuth: bool  # Is the device an OAuth device?
    # isZWave: bool  # Is the device a ZWave device.
    # managedDeviceType: int  # The type of device.
    # webSettings: int # The route where the user can edit the device settings on the web.
    # fmt: on
