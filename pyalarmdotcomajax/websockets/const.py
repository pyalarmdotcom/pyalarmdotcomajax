"""Constants for WebSocket messages."""

from enum import Enum


class PropertyChangeType(Enum):
    """Enum for property change message types."""

    # Supported
    AmbientTemperature = 1  # Expressed as 100ths of a degree F
    HeatSetPoint = 2  # Expressed as 100ths of a degree F
    CoolSetPoint = 3  # Expressed as 100ths of a degree F
    LightColor = 4

    # Unsupported
    IrrigationStatus = 5


SUPPORTED_PROPERY_CHANGE_TYPES = [
    PropertyChangeType.AmbientTemperature,
    PropertyChangeType.HeatSetPoint,
    PropertyChangeType.CoolSetPoint,
    PropertyChangeType.LightColor,
]


class EventType(Enum):
    """Enum for monitoring event types."""

    #
    # Supported
    #
    ArmedAway = 10
    ArmedNight = 113
    ArmedStay = 9
    Closed = 0
    Disarmed = 8
    DoorLocked = 91
    DoorUnlocked = 90
    ImageSensorUpload = 99
    LightTurnedOff = 316
    LightTurnedOn = 315
    Opened = 15
    OpenedClosed = 100
    SupervisionFaultArming = 48
    SupervisionFaultDisarming = 47
    SwitchLevelChanged = 317
    ThermostatFanModeChanged = 120
    ThermostatModeChanged = 95
    ThermostatOffset = 105
    ThermostatSetPointChanged = 94

    #
    # Not Supported
    #
    Alarm = 1
    BypassStart = 13
    BypassEnd = 35
    SumpPumpAlertCriticalIssueMalfunction = 118
    SumpPumpAlertCriticalIssueOff = 117
    SumpPumpAlertIdle = 114
    SumpPumpAlertNormalOperation = 115
    SumpPumpAlertPossibleIssue = 116
    VideoCameraTriggered = 71
    VideoEventTriggered = 76
    AlarmCancelled = 238
    AuxiliaryPanic = 17
    AuxPanicPendingAlarm = 61
    AuxPanicSuspectedAlarm = 65
    CommercialClosedOnTime = 127
    CommercialClosedUnexpectedly = 177
    CommercialEarlyClose = 125
    CommercialEarlyOpen = 122
    CommercialLateClose = 126
    CommercialLateOpen = 123
    CommercialOpenOnTime = 124
    DoorBuzzedFromWebsite = 182
    FirePanic = 24
    InAppAuxiliaryPanic = 201
    InAppFirePanic = 200
    InAppPolicePanic = 202
    InAppSilentPolicePanic = 203
    MonitoringPanic = 2009
    NetworkDhcpReservationsUpdated = 433
    NetworkDhcpSettingsUpdated = 432
    NetworkMapUpdated = 391
    NetworkPortForwardingUpdated = 434
    PackageDeliveryAlert = 363
    PackageRetrievalAlert = 364
    PendingAlarm = 62
    PolicePanic = 22
    PolicePanicSuspectedAlarm = 64
    SilentPolicePanic = 73
    SilentPolicePanicSuspectedAlarm = 172
    ViewedByCentralStation = 158

    # Undocumented
    UserLoggedIn = 55


SUPPORTED_MONITORING_EVENT_TYPES = [
    EventType.ArmedAway,
    EventType.ArmedNight,
    EventType.ArmedStay,
    EventType.Closed,
    EventType.Disarmed,
    EventType.DoorLocked,
    EventType.DoorUnlocked,
    EventType.ImageSensorUpload,
    EventType.LightTurnedOff,
    EventType.LightTurnedOn,
    EventType.Opened,
    EventType.OpenedClosed,
    EventType.SupervisionFaultArming,
    EventType.SupervisionFaultDisarming,
    EventType.SwitchLevelChanged,
    EventType.ThermostatFanModeChanged,
    EventType.ThermostatModeChanged,
    EventType.ThermostatOffset,
    EventType.ThermostatSetPointChanged,
]
