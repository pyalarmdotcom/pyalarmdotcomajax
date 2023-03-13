"""Device registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TypedDict

from pyalarmdotcomajax.devices import BaseDevice, DeviceType
from pyalarmdotcomajax.devices.camera import Camera
from pyalarmdotcomajax.devices.garage_door import GarageDoor
from pyalarmdotcomajax.devices.gate import Gate
from pyalarmdotcomajax.devices.image_sensor import ImageSensor
from pyalarmdotcomajax.devices.light import Light
from pyalarmdotcomajax.devices.lock import Lock
from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.devices.system import System
from pyalarmdotcomajax.devices.thermostat import Thermostat
from pyalarmdotcomajax.devices.water_sensor import WaterSensor
from pyalarmdotcomajax.errors import UnsupportedDevice
from pyalarmdotcomajax.helpers import classproperty

log = logging.getLogger(__name__)

AllDevices_t = (
    Camera
    | GarageDoor
    | Gate
    | ImageSensor
    | Light
    | Lock
    | Partition
    | Sensor
    | System
    | Thermostat
    | WaterSensor
)

AllDevicesLists_t = (
    list[Camera]
    | list[GarageDoor]
    | list[Gate]
    | list[ImageSensor]
    | list[Light]
    | list[Lock]
    | list[Partition]
    | list[Sensor]
    | list[System]
    | list[Thermostat]
    | list[WaterSensor]
)

AllDevicesDicts_t = (
    dict[str, Camera]
    | dict[str, GarageDoor]
    | dict[str, Gate]
    | dict[str, ImageSensor]
    | dict[str, Light]
    | dict[str, Lock]
    | dict[str, Partition]
    | dict[str, Sensor]
    | dict[str, System]
    | dict[str, Thermostat]
    | dict[str, WaterSensor]
)


class DeviceTypeEndpoints(TypedDict, total=False):
    """Stores endpoints for a device type."""

    primary: str
    additional: dict[str, str]


class AttributeRegistryEntry(TypedDict, total=False):
    """Stores information about a device type."""

    endpoints: DeviceTypeEndpoints
    class_: type[BaseDevice]
    supported: bool
    rel_id: str
    device_registry_property: str


@dataclass
class DeviceRegistry:
    """Stores devices by type."""

    cameras: dict[str, Camera] = field(default_factory=dict)
    garage_doors: dict[str, GarageDoor] = field(default_factory=dict)
    gates: dict[str, Gate] = field(default_factory=dict)
    image_sensors: dict[str, ImageSensor] = field(default_factory=dict)
    lights: dict[str, Light] = field(default_factory=dict)
    locks: dict[str, Lock] = field(default_factory=dict)
    partitions: dict[str, Partition] = field(default_factory=dict)
    sensors: dict[str, Sensor] = field(default_factory=dict)
    systems: dict[str, System] = field(default_factory=dict)
    thermostats: dict[str, Thermostat] = field(default_factory=dict)
    water_sensors: dict[str, WaterSensor] = field(default_factory=dict)

    ############
    ## PUBLIC ##
    ############

    def get(self, device_id: str) -> BaseDevice | None:
        """Get device by id."""

        # Selects all device buckets by pulling all variables from self, then merges into a single dict.

        return {
            key: value for d in list(vars(self).values()) for key, value in d.items()
        }.get(device_id)

    def store(self, payload: AllDevices_t | AllDevicesLists_t) -> None:
        """Store device or list of devices."""

        if isinstance(payload, list):
            self._store_devices(payload)
        if isinstance(payload, BaseDevice):
            self._store_device(payload)

    def clear(self, type_or_class: type | DeviceType) -> None:
        """Clear devices of a given type."""

        if isinstance(type_or_class, type):
            self._get_storage_by_class(type_or_class).clear()
        if isinstance(type_or_class, DeviceType):
            self._get_storage_by_devicetype(type_or_class).clear()

    #############
    ## PRIVATE ##
    #############

    def _store_device(self, device: AllDevices_t) -> None:
        """Store device in appropriate device store by class."""

        device_type = type(device)

        device_store: dict = self._get_storage_by_class(device_type)

        device_store[device.id_] = device

    def _store_devices(self, devices: AllDevicesLists_t) -> None:
        """Store devices in appropriate device store by class."""

        device_type = type(devices[0])

        device_store: dict = self._get_storage_by_class(device_type)

        device_store.clear()

        device_store.update(
            {
                device.id_: device
                for device in devices
                if isinstance(device, device_type)
            }
        )

    def _get_storage_by_class(self, device_class: type) -> AllDevicesDicts_t:
        """Get device storage for specified class."""

        storage: AllDevicesDicts_t = getattr(
            self, AttributeRegistry.get_storage_name(device_class)
        )

        return storage

    def _get_storage_by_devicetype(self, device_type: DeviceType) -> AllDevicesDicts_t:
        """Get device storage for specified device type."""

        return self._get_storage_by_class(AttributeRegistry.get_class(device_type))


class AttributeRegistry:
    """Device registry."""

    _ATTRIBUTES: dict[DeviceType, AttributeRegistryEntry] = {
        DeviceType.CAMERA: {
            "endpoints": {"primary": "{}web/api/video/devices/cameras/{}"},
            "class_": Camera,
            "rel_id": "video/camera",
            "device_registry_property": "cameras",
        },
        DeviceType.GARAGE_DOOR: {
            "endpoints": {"primary": "{}web/api/devices/garageDoors/{}"},
            "class_": GarageDoor,
            "rel_id": "devices/garage-door",
            "device_registry_property": "garage_doors",
        },
        DeviceType.GATE: {
            "endpoints": {"primary": "{}web/api/devices/gates/{}"},
            "class_": Gate,
            "rel_id": "devices/gate",
            "device_registry_property": "gates",
        },
        DeviceType.IMAGE_SENSOR: {
            "endpoints": {
                "primary": "{}web/api/imageSensor/imageSensors/{}",
                "additional": {
                    "recent_images": (
                        "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"
                    )
                },
            },
            "class_": ImageSensor,
            "rel_id": "image-sensor/image-sensor",
            "device_registry_property": "image_sensors",
        },
        DeviceType.LIGHT: {
            "endpoints": {"primary": "{}web/api/devices/lights/{}"},
            "class_": Light,
            "rel_id": "devices/light",
            "device_registry_property": "lights",
        },
        DeviceType.LOCK: {
            "endpoints": {"primary": "{}web/api/devices/locks/{}"},
            "class_": Lock,
            "rel_id": "devices/lock",
            "device_registry_property": "locks",
        },
        DeviceType.PARTITION: {
            "endpoints": {"primary": "{}web/api/devices/partitions/{}"},
            "class_": Partition,
            "rel_id": "devices/partition",
            "device_registry_property": "partitions",
        },
        DeviceType.SENSOR: {
            "endpoints": {"primary": "{}web/api/devices/sensors/{}"},
            "class_": Sensor,
            "rel_id": "devices/sensor",
            "device_registry_property": "sensors",
        },
        DeviceType.SYSTEM: {
            "endpoints": {"primary": "{}web/api/systems/systems/{}"},
            "class_": System,
            "rel_id": "systems/system",
            "device_registry_property": "systems",
        },
        DeviceType.THERMOSTAT: {
            "endpoints": {"primary": "{}web/api/devices/thermostats/{}"},
            "class_": Thermostat,
            "rel_id": "devices/thermostat",
            "device_registry_property": "thermostats",
        },
        DeviceType.WATER_SENSOR: {
            "endpoints": {"primary": "{}web/api/devices/waterSensors/{}"},
            "class_": WaterSensor,
            "rel_id": "devices/water-sensor",
            "device_registry_property": "water_sensors",
        },
        DeviceType.ACCESS_CONTROL: {
            "endpoints": {
                "primary": "{}web/api/devices/accessControlAccessPointDevices/{}"
            },
            "rel_id": "devices/access-control-access-point-device",
        },
        DeviceType.CAMERA_SD: {
            "endpoints": {"primary": "{}web/api/video/devices/sdCardCameras/{}"},
            "rel_id": "video/sd-card-camera",
        },
        DeviceType.CAR_MONITOR: {
            "endpoints": {"primary": "{}web/api/devices/carMonitors/{}"},
            "rel_id": "devices/car-monitor",
        },
        DeviceType.COMMERCIAL_TEMP: {
            "endpoints": {
                "primary": "{}web/api/devices/commercialTemperatureSensors/{}"
            },
            "rel_id": "devices/commercial-temperature-sensor",
        },
        # DeviceType.CONFIGURATION: {
        #     "endpoints": {"primary": "{}web/api/systems/configurations/{}"},
        #     "rel_id": "configuration",
        # },
        # DeviceType.FENCE: {
        #     "endpoints": {"primary": "{}web/api/geolocation/fences/{}"},
        #     "rel_id": "",
        # },
        DeviceType.GEO_DEVICE: {
            "endpoints": {"primary": "{}web/api/geolocation/geoDevices/{}"},
            "rel_id": "geolocation/geo-device",
        },
        DeviceType.IQ_ROUTER: {
            "endpoints": {"primary": "{}web/api/devices/iqRouters/{}"},
            "rel_id": "devices/iq-router",
        },
        DeviceType.REMOTE_TEMP: {
            "endpoints": {"primary": "{}web/api/devices/remoteTemperatureSensors/{}"},
            "rel_id": "devices/remote-temperature-sensor",
        },
        DeviceType.SCENE: {
            "endpoints": {"primary": "{}web/api/automation/scenes/{}"},
            "rel_id": "automation/scene",
        },
        DeviceType.SHADE: {
            "endpoints": {"primary": "{}web/api/devices/shades/{}"},
            "rel_id": "devices/shade",
        },
        DeviceType.SMART_CHIME: {
            "endpoints": {"primary": "{}web/api/devices/smartChimeDevices/{}"},
            "rel_id": "devices/smart-chime-device",
        },
        DeviceType.SUMP_PUMP: {
            "endpoints": {"primary": "{}web/api/devices/sumpPumps/{}"},
            "rel_id": "devices/sump-pump",
        },
        DeviceType.SWITCH: {
            "endpoints": {"primary": "{}web/api/devices/switches/{}"},
            "rel_id": "devices/switch",
        },
        DeviceType.VALVE_SWITCH: {
            "endpoints": {"primary": "{}web/api/devices/valveSwitches/{}"},
            "rel_id": "valve-switch",
        },
        DeviceType.WATER_METER: {
            "endpoints": {"primary": "{}web/api/devices/waterMeters/{}"},
            "rel_id": "devices/water-meter",
        },
        DeviceType.WATER_VALVE: {
            "endpoints": {"primary": "{}web/api/devices/waterValves/{}"},
            "rel_id": "devices/water-valve",
        },
        DeviceType.X10_LIGHT: {
            "endpoints": {"primary": "{}web/api/devices/x10Lights/{}"},
            "rel_id": "devices/x10-light",
        },
    }

    @staticmethod
    def is_supported(device_type: DeviceType) -> bool:
        """Return if device type is supported."""
        return (
            AttributeRegistry._ATTRIBUTES.get(device_type, {}).get("supported") is True
        )

    @staticmethod
    def get_endpoints(device_type: DeviceType) -> DeviceTypeEndpoints:
        """Return primary endpoint for device type."""
        try:
            return AttributeRegistry._ATTRIBUTES.get(device_type, {})["endpoints"]
        except KeyError as err:
            raise UnsupportedDevice from err

    @staticmethod
    def get_class(device_type: DeviceType) -> type[BaseDevice]:
        """Return primary endpoint for device type."""

        try:
            return AttributeRegistry._ATTRIBUTES.get(device_type, {})["class_"]
        except KeyError as err:
            raise UnsupportedDevice from err

    @staticmethod
    def get_storage_name(device_type: DeviceType | type) -> str:
        """Return primary endpoint for device type."""

        try:
            if isinstance(device_type, DeviceType):
                return AttributeRegistry._ATTRIBUTES.get(device_type, {})[
                    "device_registry_property"
                ]

            return next(
                attributes["device_registry_property"]
                for attributes in AttributeRegistry._ATTRIBUTES.values()
                if attributes.get("class_") == device_type
            )

        except KeyError as err:
            raise UnsupportedDevice from err

    @classproperty
    def supported_devices(cls) -> list[DeviceType]:
        """Return list of supported devices."""
        return [
            device_type
            for device_type in cls._ATTRIBUTES
            if cls._ATTRIBUTES[device_type].get("class_")
        ]

    @classproperty
    def unsupported_devices(cls) -> list[DeviceType]:
        """Return list of supported devices."""
        return [
            device_type
            for device_type in cls._ATTRIBUTES
            if not cls._ATTRIBUTES[device_type].get("class_")
        ]

    @classproperty
    def endpoints(cls) -> dict[DeviceType, DeviceTypeEndpoints]:
        """Return all endpoints for all device types."""
        return {
            device_type: cls.get_endpoints(device_type)
            for device_type in cls._ATTRIBUTES
        }
