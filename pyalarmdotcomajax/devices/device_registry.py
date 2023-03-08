"""Storage for devices."""

from __future__ import annotations
from typing import TypedDict

from anyio import Lock

from pyalarmdotcomajax.devices.camera import Camera
from pyalarmdotcomajax.devices.garage_door import GarageDoor
from pyalarmdotcomajax.devices.gate import Gate
from pyalarmdotcomajax.devices.image_sensor import ImageSensor
from pyalarmdotcomajax.devices.light import Light
from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.devices.system import System
from pyalarmdotcomajax.devices.thermostat import Thermostat
from pyalarmdotcomajax.devices.water_sensor import WaterSensor


class DeviceStore(TypedDict, total=False):
    """Stores devices by type."""

    # Names must be kept in sync with DeviceType enum.

    cameras: dict[str, Camera]
    garageDoors: dict[str, GarageDoor]
    gates: dict[str, Gate]
    imageSensors: dict[str, ImageSensor]
    lights: dict[str, Light]
    locks: dict[str, Lock]
    partitions: dict[str, Partition]
    sensors: dict[str, Sensor]
    systems: dict[str, System]
    thermostats: dict[str, Thermostat]
    waterSensors: dict[str, WaterSensor]
