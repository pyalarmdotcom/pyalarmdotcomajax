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
from pyalarmdotcomajax.devices.scene import Scene
from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.devices.system import System
from pyalarmdotcomajax.devices.thermostat import Thermostat
from pyalarmdotcomajax.devices.water_sensor import WaterSensor
from pyalarmdotcomajax.exceptions import UnknownDevice, UnsupportedDeviceType
from pyalarmdotcomajax.helpers import classproperty
from pyalarmdotcomajax.models import DeviceRelationshipTypeId, DeviceTypeId

log = logging.getLogger(__name__)


ATTRIBUTES: dict[DeviceType, AttributeRegistryEntry] = {
    DeviceType.CAMERA: {
        "endpoints": {"primary": "{}web/api/video/devices/cameras/{}"},
        "class_": Camera,
        "rel_id": DeviceRelationshipTypeId.CAMERA.value,
        "type_id": DeviceTypeId.CAMERA.value,
        "device_registry_property": "cameras",
    },
    DeviceType.GARAGE_DOOR: {
        "endpoints": {"primary": "{}web/api/devices/garageDoors/{}"},
        "class_": GarageDoor,
        "rel_id": DeviceRelationshipTypeId.GARAGE_DOOR.value,
        "type_id": DeviceTypeId.GARAGE_DOOR.value,
        "device_registry_property": "garage_doors",
    },
    DeviceType.GATE: {
        "endpoints": {"primary": "{}web/api/devices/gates/{}"},
        "class_": Gate,
        "rel_id": DeviceRelationshipTypeId.GATE.value,
        "type_id": DeviceTypeId.GATE.value,
        "device_registry_property": "gates",
    },
    DeviceType.IMAGE_SENSOR: {
        "endpoints": {
            "primary": "{}web/api/imageSensor/imageSensors/{}",
            "additional": {"recent_images": "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"},
        },
        "class_": ImageSensor,
        "rel_id": DeviceRelationshipTypeId.IMAGE_SENSOR.value,
        "type_id": DeviceTypeId.IMAGE_SENSOR.value,
        "device_registry_property": "image_sensors",
    },
    DeviceType.LIGHT: {
        "endpoints": {"primary": "{}web/api/devices/lights/{}"},
        "class_": Light,
        "rel_id": DeviceRelationshipTypeId.LIGHT.value,
        "type_id": DeviceTypeId.LIGHT.value,
        "device_registry_property": "lights",
    },
    DeviceType.LOCK: {
        "endpoints": {"primary": "{}web/api/devices/locks/{}"},
        "class_": Lock,
        "rel_id": DeviceRelationshipTypeId.LOCK.value,
        "type_id": DeviceTypeId.LOCK.value,
        "device_registry_property": "locks",
    },
    DeviceType.PARTITION: {
        "endpoints": {"primary": "{}web/api/devices/partitions/{}"},
        "class_": Partition,
        "rel_id": DeviceRelationshipTypeId.PARTITION.value,
        "type_id": DeviceTypeId.PARTITION.value,
        "device_registry_property": "partitions",
    },
    DeviceType.SCENE: {
        "endpoints": {"primary": "{}web/api/automation/scenes/{}"},
        "class_": Scene,
        "rel_id": DeviceRelationshipTypeId.SCENE.value,
        "type_id": DeviceTypeId.SCENE.value,
        "device_registry_property": "scenes",
    },
    DeviceType.SENSOR: {
        "endpoints": {"primary": "{}web/api/devices/sensors/{}"},
        "class_": Sensor,
        "rel_id": DeviceRelationshipTypeId.SENSOR.value,
        "type_id": DeviceTypeId.SENSOR.value,
        "device_registry_property": "sensors",
    },
    DeviceType.SYSTEM: {
        "endpoints": {"primary": "{}web/api/systems/systems/{}"},
        "class_": System,
        "rel_id": DeviceRelationshipTypeId.SYSTEM.value,
        "type_id": DeviceTypeId.SYSTEM.value,
        "device_registry_property": "systems",
    },
    DeviceType.THERMOSTAT: {
        "endpoints": {"primary": "{}web/api/devices/thermostats/{}"},
        "class_": Thermostat,
        "rel_id": DeviceRelationshipTypeId.THERMOSTAT.value,
        "type_id": DeviceTypeId.THERMOSTAT.value,
        "device_registry_property": "thermostats",
    },
    DeviceType.WATER_SENSOR: {
        "endpoints": {"primary": "{}web/api/devices/waterSensors/{}"},
        "class_": WaterSensor,
        "rel_id": DeviceRelationshipTypeId.WATER_SENSOR.value,
        "type_id": DeviceTypeId.WATER_SENSOR.value,
        "device_registry_property": "water_sensors",
    },
    DeviceType.ACCESS_CONTROL: {
        "endpoints": {"primary": "{}web/api/devices/accessControlAccessPointDevices/{}"},
        "rel_id": DeviceRelationshipTypeId.ACCESS_CONTROL.value,
        "type_id": DeviceTypeId.ACCESS_CONTROL.value,
    },
    DeviceType.CAMERA_SD: {
        "endpoints": {"primary": "{}web/api/video/devices/sdCardCameras/{}"},
        "rel_id": DeviceRelationshipTypeId.CAMERA_SD.value,
        "type_id": DeviceTypeId.CAMERA_SD.value,
    },
    DeviceType.CAR_MONITOR: {
        "endpoints": {"primary": "{}web/api/devices/carMonitors/{}"},
        "rel_id": DeviceRelationshipTypeId.CAR_MONITOR.value,
        "type_id": DeviceTypeId.CAR_MONITOR.value,
    },
    DeviceType.COMMERCIAL_TEMP: {
        "endpoints": {"primary": "{}web/api/devices/commercialTemperatureSensors/{}"},
        "rel_id": DeviceRelationshipTypeId.COMMERCIAL_TEMP.value,
        "type_id": DeviceTypeId.COMMERCIAL_TEMP.value,
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
        "rel_id": DeviceRelationshipTypeId.GEO_DEVICE.value,
        "type_id": DeviceTypeId.GEO_DEVICE.value,
    },
    DeviceType.IQ_ROUTER: {
        "endpoints": {"primary": "{}web/api/devices/iqRouters/{}"},
        "rel_id": DeviceRelationshipTypeId.IQ_ROUTER.value,
        "type_id": DeviceTypeId.IQ_ROUTER.value,
    },
    DeviceType.REMOTE_TEMP: {
        "endpoints": {"primary": "{}web/api/devices/remoteTemperatureSensors/{}"},
        "rel_id": DeviceRelationshipTypeId.REMOTE_TEMP.value,
        "type_id": DeviceTypeId.REMOTE_TEMP.value,
    },
    DeviceType.SHADE: {
        "endpoints": {"primary": "{}web/api/devices/shades/{}"},
        "rel_id": DeviceRelationshipTypeId.SHADE.value,
        "type_id": DeviceTypeId.SHADE.value,
    },
    DeviceType.SMART_CHIME: {
        "endpoints": {"primary": "{}web/api/devices/smartChimeDevices/{}"},
        "rel_id": DeviceRelationshipTypeId.SMART_CHIME.value,
        "type_id": DeviceTypeId.SMART_CHIME.value,
    },
    DeviceType.SUMP_PUMP: {
        "endpoints": {"primary": "{}web/api/devices/sumpPumps/{}"},
        "rel_id": DeviceRelationshipTypeId.SUMP_PUMP.value,
        "type_id": DeviceTypeId.SUMP_PUMP.value,
    },
    DeviceType.SWITCH: {
        "endpoints": {"primary": "{}web/api/devices/switches/{}"},
        "rel_id": DeviceRelationshipTypeId.SWITCH.value,
        "type_id": DeviceTypeId.SWITCH.value,
    },
    DeviceType.VALVE_SWITCH: {
        "endpoints": {"primary": "{}web/api/devices/valveSwitches/{}"},
        "rel_id": DeviceRelationshipTypeId.VALVE_SWITCH.value,
        "type_id": DeviceTypeId.VALVE_SWITCH.value,
    },
    DeviceType.WATER_METER: {
        "endpoints": {"primary": "{}web/api/devices/waterMeters/{}"},
        "rel_id": DeviceRelationshipTypeId.WATER_METER.value,
        "type_id": DeviceTypeId.WATER_METER.value,
    },
    DeviceType.WATER_VALVE: {
        "endpoints": {"primary": "{}web/api/devices/waterValves/{}"},
        "rel_id": DeviceRelationshipTypeId.WATER_VALVE.value,
        "type_id": DeviceTypeId.WATER_VALVE.value,
    },
    DeviceType.X10_LIGHT: {
        "endpoints": {"primary": "{}web/api/devices/x10Lights/{}"},
        "rel_id": DeviceRelationshipTypeId.X10_LIGHT.value,
        "type_id": DeviceTypeId.X10_LIGHT.value,
    },
}


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
    type_id: str
    device_registry_property: str


@dataclass
class DeviceRegistry(BaseDevice):
    """Stores devices by type."""

    _devices: dict[str, BaseDevice] = field(default_factory=dict)

    ############
    ## PUBLIC ##
    ############

    @property
    def all(self) -> dict[str, BaseDevice]:
        """Return devices."""
        return self._devices

    def get(self, device_id: str) -> BaseDevice:
        """Get device by id."""

        try:
            return self._devices[device_id]
        except KeyError as err:
            raise UnknownDevice(device_id) from err

    def update(self, payload: dict[str, BaseDevice], purge: bool = False) -> None:
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
    def scenes(self) -> dict[str, Scene]:
        """Return sensors."""
        return {device_id: device for device_id, device in self._devices.items() if type(device) == Scene}

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

    @staticmethod
    def is_supported(device_type: DeviceType) -> bool:
        """Return if device type is supported."""
        return ATTRIBUTES.get(device_type, {}).get("class_") is not None

    @staticmethod
    def get_endpoints(device_type: DeviceType) -> DeviceTypeEndpoints:
        """Return primary endpoint for device type."""
        try:
            return ATTRIBUTES.get(device_type, {})["endpoints"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @staticmethod
    def get_class(device_type: DeviceType) -> type[BaseDevice]:
        """Return primary endpoint for device type."""

        try:
            return ATTRIBUTES[device_type]["class_"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @staticmethod
    def get_storage_name(device_type: DeviceType | type) -> str:
        """Return primary endpoint for device type."""

        try:
            if isinstance(device_type, DeviceType):
                return ATTRIBUTES.get(device_type, {})["device_registry_property"]

            return next(
                attributes["device_registry_property"]
                for attributes in ATTRIBUTES.values()
                if attributes.get("class_") == device_type
            )

        except KeyError as err:
            raise UnsupportedDeviceType(str(device_type)) from err

    @staticmethod
    def get_devicetype_from_relationship_id(relationship_id: str) -> DeviceType:
        """Return device type from relationship id."""
        for device_type, attributes in ATTRIBUTES.items():
            if attributes.get("rel_id") == relationship_id:
                return device_type

        raise UnsupportedDeviceType(relationship_id)

    @staticmethod
    def get_relationship_id_from_devicetype(device_type: DeviceType) -> str:
        """Return device type from relationship id."""
        try:
            return ATTRIBUTES[device_type]["rel_id"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @staticmethod
    def get_type_id_from_devicetype(device_type: DeviceType) -> str:
        """Return device type from relationship id."""
        try:
            return ATTRIBUTES[device_type]["type_id"]
        except KeyError as err:
            raise UnsupportedDeviceType(device_type) from err

    @classproperty
    def supported_device_types(cls) -> list[DeviceType]:  # pylint: disable=no-self-argument
        """Return list of supported devices."""
        return [device_type for device_type in ATTRIBUTES if ATTRIBUTES[device_type].get("class_")]

    @classproperty
    def unsupported_device_types(cls) -> list[DeviceType]:  # pylint: disable=no-self-argument
        """Return list of supported devices."""
        return [device_type for device_type in ATTRIBUTES if not ATTRIBUTES[device_type].get("class_")]

    @classproperty
    def endpoints(cls) -> dict[DeviceType, DeviceTypeEndpoints]:  # pylint: disable=no-self-argument
        """Return all endpoints for all device types."""
        return {device_type: cls.get_endpoints(device_type) for device_type in ATTRIBUTES}

    @classproperty
    def all_relationship_ids(cls) -> list[str]:  # pylint: disable=no-self-argument
        """Return all relationship ids for all device types."""
        return [device_type["rel_id"] for device_type in ATTRIBUTES.values()]
