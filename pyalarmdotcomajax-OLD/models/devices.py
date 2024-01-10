"""Alarm.com API models."""

from abc import ABC
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Generic, TypeAlias, TypeVar

from mashumaro import field_options

from pyalarmdotcomajax.models.api import BaseElement

DeviceState = TypeVar("DeviceState", bound=IntEnum)

#
# GENERIC
#


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


@dataclass
class DeviceRelationshipEntry(BaseElement):
    """Device relationship."""

    id_: str = field(metadata=field_options(alias="id"))
    type: DeviceRelationshipTypeId


#
# BASE DEVICE
#


class BaseDevice(ABC, BaseElement):
    """Base device."""


class BaseStatefulDeviceState(IntEnum):
    """Base device state."""

    LOADING_STATE = -1


@dataclass
class BaseStatefulDeviceDescription(BaseDevice, ABC, Generic[DeviceState]):
    """Description of base device."""

    batteryLevelNull: int | None  # The current device battery level with null as the default value.
    canBeSaved: bool  # Does the logged in context have write permissions for this device?
    canChangeState: bool  # Can the state be changed for this device?
    canConfirmStateChange: bool  # Can the device confirm that its state changed?
    canReceiveCommands: bool  # Does this device support commands being sent to it?
    criticalBattery: bool  # Whether the device has a critical battery status.
    description: str  # Device name
    desiredState: BaseStatefulDeviceState | DeviceState  # The desired device state.
    hasPermissionToChangeState: bool  # Can the logged in login change the state of this device?
    isRefreshingState: bool  # Whether the device is in the refreshing state.
    lowBattery: bool  # Whether the device has a low battery status.
    remoteCommandsEnabled: bool  # Can the device status be changed remotely via app or web?
    state: BaseStatefulDeviceState | DeviceState  # The current device state.
    system: str  # ID of the corresponding system.

    # animationState: str  # The model animation state.
    # canChangeDescription: bool  # Can the device description be changed?
    # deviceIcon: int  # The icon to present the device.
    # displayDate  # Returns the display string for the current stateInfo value.
    # stateInfo: dict  # ID for StateInfo object containing extended state information.
    # stateSubtext  # The model state subtext for home cards.


#
# BASE MANAGED DEVICE
#


@dataclass
class BaseManagedDeviceDescription(BaseStatefulDeviceDescription[DeviceState], ABC):
    """Description of base managed device."""

    hasState: bool  # Does this device have a state?
    isMalfunctioning: bool  # Is the device currently set to a malfunction state.
    macAddress: str  # The mac address for the device, if available.
    manufacturer: str  # The manufacturer of the device.

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


#
# LIGHT
#


class _LightState(IntEnum):
    """Light states."""

    OFFLINE = 0
    NO_STATE = 1
    ON = 2
    OFF = 3
    LEVEL_CHANGE = 4


class LightColorFormat(IntEnum):
    """Light color formats."""

    NOT_SET = 0
    RGBW = 1
    RGB = 2
    WARM_TO_COOL = 3
    HSV = 4


LightState = BaseStatefulDeviceState | _LightState


@dataclass
class LightDescription(BaseManagedDeviceDescription[LightState], BaseElement):
    """Description of light."""

    canEnableRemoteCommands: bool  # Can the remote commands be enabled or disabled?
    canEnableStateTracking: bool  # Can state tracking be enabled for this light?
    hexColor: str | None  # A hex string representing the currently active color. For decoding this should be used in conjunction with 'lightColorFormat'.
    isDimmer: bool  # Is the light a dimmer?
    lightColorFormat: LightColorFormat  # The format of the color hex string. This values maps in the LightColorFormat enum. Defaults to "Not Set".
    lightLevel: int  # Dimmer value for a dimmer light
    percentWarmth: int  # Represents a percentage from 0-100, the color temperature is between the minimum (cool) and maximum (100% warm) temperatures we support.
    remoteCommandsEnabled: bool  # Whether remote commands are enabled or not.
    stateTrackingEnabled: bool  # Is state tracking enabled?
    supportsColorControl: bool  # Does it support any color changes?
    supportsRGBColorControl: bool  # Does it support RGB color changing?
    supportsWhiteLightColorControl: bool  # Does it support color temperature changing? (Selecting between variations of white light).

    # isFavorite: bool  # Is the light in the Favorites Group?
    # isZWave: bool  # Is the light a ZWave device.
    # lightGroups: bool  # Light groups that this light belongs to
    # shouldShowFavoritesToggle: bool  # Should the "Favorites" toggle be shown in the edit light modal?
    # shouldUpdateMultiLevelState: bool  # Whether or not we should update multilevel state as part of saving this model. Used to avoid turning on a multilevel light when updating non-lighting properties such as device name


#
# LOCK
#


class _LockState(IntEnum):
    """Lock states."""

    UNKNOWN = 0
    LOCKED = 1
    UNLOCKED = 2
    HIDDEN = 3


LockState = BaseStatefulDeviceState | _LockState


@dataclass
class LockDescription(BaseManagedDeviceDescription[LockState], BaseElement):
    """Description of lock."""

    supportsLatchControl: bool  # Whether the lock supports remotely controlling the latch.

    # availableTemporaryAccessCodes: int | None  # The number of available Temporary Access Codes that were pushed to the locks on the unit.
    # canEnableRemoteCommands: bool  # Can the remote commands be enabled or disabled? (Only for control point locks)
    # maxUserCodeLength: int  # The maximum user code length this lock supports.
    # supportsScheduledUserCodes: bool  # Whether the lock supports scheduled user code programming.
    # supportsTemporaryUserCodes: bool  # Whether the lock supports temporary user code programming.
    # totalTemporaryAccessCodes: int | None  # The total number of Temporary Access Codes that were pushed to the locks.


#
# PARTITION
#


class _PartitionState(IntEnum):
    """Partition states."""

    UNKNOWN = 0
    DISARMED = 1
    ARMED_STAY = 2
    ARMED_AWAY = 3
    ARMED_NIGHT = 4
    HIDDEN = 5


class ExtendedArmingOptions(IntEnum):
    """Partition arming options."""

    BYPASS_SENSORS = 0
    NO_ENTRY_DELAY = 1
    SILENT_ARMING = 2
    NIGHT_ARMING = 3
    SELECTIVELY_BYPASS_SENSORS = 4
    FORCE_ARM = 5
    INSTANT_ARM = 6
    STAY_ARM = 7
    AWAY_ARM = 8


PartitionState = BaseStatefulDeviceState | _PartitionState


@dataclass
class PartitionDescription(BaseManagedDeviceDescription[PartitionState]):
    """Description of partition."""

    # fmt: off
    canBypassSensorWhenArmed: bool  # Indicates the panel supports sending bypass commands when the panel is armed.
    extendedArmingOptions: list[ExtendedArmingOptions]  # The extended arming options supported per arming mode.
    hasOpenBypassableSensors: bool  # Indicates whether the partition has any open sensors related to "Force Bypass" option.
    hasSensorInTroubleCondition: bool  # Indicates whether the partition has any trouble condition related to "Force Bypass" option.
    hideForceBypass: bool  # Indicates whether the force bypass checkbox should be hidden.
    invalidExtendedArmingOptions: list[ExtendedArmingOptions]  # The extended arming option combinations that are invalid for each arming mode.
    needsClearIssuesPrompt: bool  # Should we prompt about present issues before allowing the user to arm?
    partitionId: str  # The ID for this partition.
    # fmt: on

    # canAccessPanelWifi: bool  # Can this partition access panel-wifi route?
    # canEnableAlexa: bool  # Can this partition enable Alexa features?
    # dealerEnforcesForceBypass: bool  # Indicates whether to warn the user if a sensor is open while trying to arm the panel.
    # isAlexaEnabled: bool  # Are Alexa features enabled on this partition?
    # sensorNamingFormat: int  # The allowed device naming format.
    # showNewForceBypass: bool  # Indicates whether we show the new force bypass with new text


#
# SENSOR & WATER SENSOR
#


class _SensorState(IntEnum):
    """Sensor states."""

    UNKNOWN = 0
    CLOSED = 1
    OPEN = 2
    IDLE = 3
    ACTIVE = 4
    DRY = 5
    WET = 6
    FULL = 7
    LOW = 8
    OPENED_CLOSED = 9
    ISSUE = 10
    OK = 11


SensorState = BaseStatefulDeviceState | _SensorState


@dataclass
class SensorDescription(BaseManagedDeviceDescription[SensorState]):
    """Description of sensor."""

    isBypassed: bool  # Indicates this sensor is bypassed.
    isFlexIO: bool  # Indicates if this sensor is a flex IO sensor.
    isMonitoringEnabled: bool  # Does the sensor have normal activity monitoring enabled?
    supportsBypass: bool  # Indicates this sensor supports bypass.
    supportsImmediateBypass: bool  # Indicates this sensor supports bypass outside an arming event.

    # deviceRole: int  # Indicates the current role of the sensor.
    # openClosedStatus: int  # Indicates if this sensor is in an "Open" or "Closed" state.
    # sensorNamingFormat: int  # The allowed sensor naming format.


WaterSensorDescription = TypeAlias[SensorDescription]
WaterSensorState = TypeAlias[SensorState]

#
# THERMOSTAT
#


@dataclass
class TemperatureDeviceDescription(BaseManagedDeviceDescription[DeviceState], ABC):
    """Description of temperature device."""

    ambientTemp: float  # The current temperature reported by the device.
    hasRtsIssue: bool  # Does this device have a Rts issue?
    humidityLevel: int  # The current humidity level reported by the device.
    isPaired: bool  # Is this device paired to another?
    supportsHumidity: bool  # Whether the device supports humidity.

    # supportsPairing: bool # Does this device support pairing? Does a thermostat support pairing to temperature sensors or does a temperature sensor support pairing to thermostats?
    # tempForwardingActive: bool # Is this device's temperature currently being used to drive itself or another device?


class _ThermostatState(IntEnum):
    """Thermostat states."""

    UNKNOWN = 0
    OFF = 1
    HEAT = 2
    COOL = 3
    AUTO = 4
    AUXHEAT = 5


ThermostatState = BaseStatefulDeviceState | _ThermostatState


class ThermostatFanMode(IntEnum):
    """Thermostat fan modes."""

    AUTO_LOW = 0
    ON_LOW = 1
    AUTO_HIGH = 2
    ON_HIGH = 3
    AUTO_MEDIUM = 4
    ON_MEDIUM = 5
    CIRCULATE = 6
    HUMIDITY = 7


class ThermostatScheduleMode(IntEnum):
    """Thermostat schedule modes."""

    MANUAL_MODE = 0
    SCHEDULED = 1
    SMART_SCHEDULES = 2


class TemperatureUnit(IntEnum):
    """Temperature units."""

    FAHRENHEIT = 1
    CELSIUS = 2
    KELVIN = 3


@dataclass
class ThermostatDescription(TemperatureDeviceDescription[_ThermostatState]):
    """Description of temperature device."""

    autoSetpointBuffer: float  # The minimum buffer between the heat and cool setpoints.
    awayCoolSetpoint: float  # The away preset cool setpoint.
    awayHeatSetpoint: float  # The away preset heat setpoint.
    coolSetpoint: float  # The current cool setpoint.
    desiredCoolSetpoint: float  # The desired cool setpoint.
    desiredFanMode: ThermostatFanMode  # The desired fan mode.
    desiredHeatSetpoint: float  # The desired heat setpoint.
    fanDuration: int | None  # The duration to run the fan. Only used to offset the commands.
    fanMode: ThermostatFanMode  # The current fan mode.
    forwardingAmbientTemp: float  # The current temperature including any additional temperature sensor averaging.
    hasDirtySetpoint: bool  # Does the thermostat have a setpoint that is currently being changed?
    hasPendingSetpointChange: bool  # Does the thermostat have a pending setpoint change?
    hasPendingTempModeChange: bool  # Does the thermostat have a pending temp mode change?
    heatSetpoint: float  # The current heat setpoint.
    inferredState: str  # The mode we think the thermostat is using when in auto mode (auto heat or auto cool)
    isControlled: bool  # Whether the thermostat is controlled by another thermostat.
    isPoolController: bool  # Whether the thermostat is a pool controller.
    maxAuxHeatSetpoint: float  # The max valid aux heat setpoint.
    maxCoolSetpoint: float  # The max valid cool setpoint.
    maxHeatSetpoint: float  # The max valid heat setpoint.
    minAuxHeatSetpoint: float  # The min valid aux heat setpoint.
    minCoolSetpoint: float  # The min valid cool setpoint.
    minHeatSetpoint: float  # The min valid heat setpoint.
    requiresSetup: bool  # Does the thermostat require a setup wizard to be run before being used?
    scheduleMode: str  # The schedule mode.
    setpointOffset: float  # The amount to increment or decrement the setpoint by when changing it.
    supportedFanDurations: list[int]  # The fan mode durations that the thermostat supports
    supportsAutoMode: bool  # Whether the thermostat supports the auto temp mode.
    supportsAuxHeatMode: bool  # Whether the thermostat supports the aux heat temp mode.
    supportsCirculateFanModeAlways: bool  # Whether the thermostat supports the circulate fan mode regardless of temp mode.
    supportsCirculateFanModeWhenOff: bool  # Whether the thermostat supports the circulate fan mode when in OFF mode.
    supportsCoolMode: bool  # Whether the thermostat supports the cool temp mode.
    supportsFanMode: bool  # Whether the thermostat supports fan mode control.
    supportsHeatMode: bool  # Whether the thermostat supports the heat temp mode.
    supportsIndefiniteFanOn: bool  # Whether the thermostat supports running the fan indefinitely.
    supportsOffMode: bool  # Whether the thermostat supports the off temp mode.
    supportsSchedules: bool  # Whether the thermostat supports schedules.
    supportsSetpoints: bool  # Whether the thermostat supports setpoints.

    # activeSensors: list[str]  # The collection of sensors (including the thermostat) that are currently driving the HVAC system.
    # boilerControlSystem: str  # The boiler control system this device belongs to.
    # controlledThermostats: list[str]  # The thermostats that this thermostat controls
    # coolRtsPresets: list[float]  # The paired RTS devices on cool mode, separated by setpoint.
    # desiredLocalDisplayLockingMode: str  # The desired local display locking mode.
    # hasRtsIssue: bool  # Indicates an issue with RTS forwarding.
    # heatRtsPresets: list[float]  # The paired RTS devices on heat mode, separated by setpoint.
    # homeCoolSetpoint: float  # The home preset cool setpoint.
    # homeHeatSetpoint: float  # The home preset heat setpoint.
    # localDisplayLockingMode: str  # The current local display locking mode.
    # peakProtect: bool  # The Peak Protect
    # pendingStateChanges: list[str]  # Property that contains state changes to be committed
    # remoteTemperatureSensors: list[str]  # The remote temperature sensors associated with the thermostat.
    # ruleSuggestions: list[str]  # An array of rule alerts for this thermostat.
    # scheduleIconName: str  # The name for the schedule icon.
    # sleepCoolSetpoint: float  # The sleep preset cool setpoint.
    # sleepHeatSetpoint: float  # The sleep preset heat setpoint.
    # supportsHvacAnalytics: bool  # Whether the thermostat supports HVAC Analytics.
    # supportsLocalDisplayLocking: bool  # Whether the thermostat supports local display locking.
    # supportsPartialLocalDisplayLocking: bool  # Whether the thermostat supports partial local display locking.
    # supportsSmartSchedules: bool  # Whether the thermostat supports the Smart Schedule mode.
    # supportsThirdPartySettings: bool  # Whether the thermostat supports third party settings.
    # thermostatSettingsTemplate: str  # The thermostat settings template applied to this thermostat.
    # thirdPartySettingsUrl: str  # The URL for third party settings.
    # thirdPartySettingsUrlDesc: str  # The description for third party settings URL.
    # valveSwitches: list[str]  # The valve switches associated with the thermostat.


#
# SENSOR & WATER SENSOR
#


@dataclass
class AlarmSystemDescription(BaseDevice):
    """Description of alarm system."""

    description: str
    hasSnapShotCameras: bool
    supportsSecureArming: bool
    remainingImageQuota: int
    systemGroupName: str
    unitId: int
    accessControlCurrentSystemMode: int
    isInPartialLockdown: bool
    icon: str
