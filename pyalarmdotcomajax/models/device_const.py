"""Alarm.com API models."""


#
# GENERIC
#


from enum import StrEnum


class DeviceRelationshipTypeId(StrEnum):
    """Device relationship types."""

    CAMERA = "video/camera"
    GARAGE_DOOR = "devices/garage-door"
    GATE = "devices/gate"
    IMAGE_SENSOR = "image-sensor/image-sensor"
    LIGHT = "devices/light"
    LOCK = "devices/lock"
    PARTITION = "devices/partition"
    SCENE = "automation/scene"
    SENSOR = "devices/sensor"
    SYSTEM = "systems/system"
    THERMOSTAT = "devices/thermostat"
    WATER_SENSOR = "devices/water-sensor"
    ACCESS_CONTROL = "devices/access-control-access-point-device"
    CAMERA_SD = "video/sd-card-camera"
    CAR_MONITOR = "devices/car-monitor"
    COMMERCIAL_TEMP = "devices/commercial-temperature-sensor"
    GEO_DEVICE = "geolocation/geo-device"
    IQ_ROUTER = "devices/iq-router"
    REMOTE_TEMP = "devices/remote-temperature-sensor"
    SHADE = "devices/shade"
    SMART_CHIME = "devices/smart-chime-device"
    SUMP_PUMP = "devices/sump-pump"
    SWITCH = "devices/switch"
    VALVE_SWITCH = "valve-switch"
    WATER_METER = "devices/water-meter"
    WATER_VALVE = "devices/water-valve"
    X10_LIGHT = "devices/x10-light"


class DeviceTypeId(StrEnum):
    """Device type ids as returned by the ADC API."""

    CAMERA = "cameras"
    GARAGE_DOOR = "garageDoors"
    GATE = "gates"
    IMAGE_SENSOR = "imageSensors"
    LIGHT = "lights"
    LOCK = "locks"
    PARTITION = "partitions"
    SCENE = "scenes"
    SENSOR = "sensors"
    SYSTEM = "systems"
    THERMOSTAT = "thermostats"
    WATER_SENSOR = "waterSensors"
    ACCESS_CONTROL = "accessControlAccessPointDevices"
    CAMERA_SD = "sdCardCameras"
    CAR_MONITOR = "carMonitors"
    COMMERCIAL_TEMP = "commercialTemperatureSensors"
    GEO_DEVICE = "geoDevices"
    IQ_ROUTER = "iqRouters"
    REMOTE_TEMP = "remoteTemperatureSensors"
    SHADE = "shades"
    SMART_CHIME = "smartChimeDevices"
    SUMP_PUMP = "sumpPumps"
    SWITCH = "switches"
    VALVE_SWITCH = "valveSwitches"
    WATER_METER = "waterMeters"
    WATER_VALVE = "waterValves"
    X10_LIGHT = "x10Lights"
