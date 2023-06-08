"""Device registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TypedDict

from pyalarmdotcomajax.devices import DeviceType
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
from pyalarmdotcomajax.exceptions import UnkonwnDevice, UnsupportedDeviceType
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

AllDeviceTypes_t = (
    type[Camera]
    | type[GarageDoor]
    | type[Gate]
    | type[ImageSensor]
    | type[Light]
    | type[Lock]
    | type[Partition]
    | type[Sensor]
    | type[System]
    | type[Thermostat]
    | type[WaterSensor]
)

# AllCommands_t = (
#     Camera.Command
#     | GarageDoor.Command
#     | Gate.Command
#     | ImageSensor.Command
#     | Light.Command
#     | Lock.Command
#     | Partition.Command
#     | Sensor.Command
#     | System.Command
#     | Thermostat.Command
#     | WaterSensor.Command
# )


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
    class_: AllDeviceTypes_t
    supported: bool
    rel_id: str
    device_registry_property: str


@dataclass
class DeviceRegistry:
    """Stores devices by type."""

    _devices: dict[str, AllDevices_t] = field(default_factory=dict)

    ############
    ## PUBLIC ##
    ############

    @property
    def all(self) -> dict[str, AllDevices_t]:
        """Return devices."""
        return self._devices

    def get(self, device_id: str) -> AllDevices_t:
        """Get device by id."""

        try:
            return self._devices[device_id]
        except KeyError as err:
            raise UnkonwnDevice(device_id) from err

    def update(self, payload: dict[str, AllDevices_t], purge: bool = False) -> None:
        """Store device or list of devices."""

        if purge:
            self._devices = payload
        else:
            self._devices.update(payload)

    @property
    def cameras(self) -> dict[str, Camera]:
        """Return cameras."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Camera}

    @property
    def garage_doors(self) -> dict[str, GarageDoor]:
        """Return garage doors."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == GarageDoor}

    @property
    def gates(self) -> dict[str, Gate]:
        """Return gates."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Gate}

    @property
    def image_sensors(self) -> dict[str, ImageSensor]:
        """Return image sensors."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == ImageSensor}

    @property
    def lights(self) -> dict[str, Light]:
        """Return lights."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Light}

    @property
    def locks(self) -> dict[str, Lock]:
        """Return locks."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Lock}

    @property
    def partitions(self) -> dict[str, Partition]:
        """Return partitions."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Partition}

    @property
    def sensors(self) -> dict[str, Sensor]:
        """Return sensors."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Sensor}

    @property
    def systems(self) -> dict[str, System]:
        """Return systems."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == System}

    @property
    def thermostats(self) -> dict[str, Thermostat]:
        """Return thermostats."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Thermostat}

    @property
    def water_sensors(self) -> dict[str, WaterSensor]:
        """Return water sensors."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == WaterSensor}


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
                "additional": {"recent_images": "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"},
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
            "endpoints": {"primary": "{}web/api/devices/accessControlAccessPointDevices/{}"},
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
            "endpoints": {"primary": "{}web/api/devices/commercialTemperatureSensors/{}"},
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
        return AttributeRegistry._ATTRIBUTES.get(device_type, {}).get("class_") is not None

    @staticmethod
    def get_endpoints(device_type: DeviceType) -> DeviceTypeEndpoints:
        """Return primary endpoint for device type."""
        try:
            return AttributeRegistry._ATTRIBUTES.get(device_type, {})["endpoints"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @staticmethod
    def get_class(device_type: DeviceType) -> type[AllDevices_t]:
        """Return primary endpoint for device type."""

        try:
            return AttributeRegistry._ATTRIBUTES[device_type]["class_"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @staticmethod
    def get_storage_name(device_type: DeviceType | type) -> str:
        """Return primary endpoint for device type."""

        try:
            if isinstance(device_type, DeviceType):
                return AttributeRegistry._ATTRIBUTES.get(device_type, {})["device_registry_property"]

            return next(
                attributes["device_registry_property"]
                for attributes in AttributeRegistry._ATTRIBUTES.values()
                if attributes.get("class_") == device_type
            )

        except KeyError as err:
            raise UnsupportedDeviceType(str(device_type)) from err

    @staticmethod
    def get_devicetype_from_relationship_id(relationship_id: str) -> DeviceType:
        """Return device type from relationship id."""
        for device_type, attributes in AttributeRegistry._ATTRIBUTES.items():
            if attributes.get("rel_id") == relationship_id:
                return device_type

        raise UnsupportedDeviceType(relationship_id)

    @staticmethod
    def get_relationship_id_from_devicetype(device_type: DeviceType) -> str:
        """Return device type from relationship id."""
        try:
            return AttributeRegistry._ATTRIBUTES[device_type]["rel_id"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @classproperty
    def supported_device_types(cls) -> list[DeviceType]:  # pylint: disable=no-self-argument
        """Return list of supported devices."""
        return [device_type for device_type in cls._ATTRIBUTES if cls._ATTRIBUTES[device_type].get("class_")]

    @classproperty
    def unsupported_device_types(cls) -> list[DeviceType]:  # pylint: disable=no-self-argument
        """Return list of supported devices."""
        return [device_type for device_type in cls._ATTRIBUTES if not cls._ATTRIBUTES[device_type].get("class_")]

    @classproperty
    def endpoints(cls) -> dict[DeviceType, DeviceTypeEndpoints]:  # pylint: disable=no-self-argument
        """Return all endpoints for all device types."""
        return {device_type: cls.get_endpoints(device_type) for device_type in cls._ATTRIBUTES}

    @classproperty
    def all_relationship_ids(cls) -> list[str]:  # pylint: disable=no-self-argument
        """Return all relationship ids for all device types."""
        return [device_type["rel_id"] for device_type in cls._ATTRIBUTES.values()]
