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
    """Enum for event types."""

    # Supported
    ArmedAway = 10
    ArmedNight = 113
    ArmedStay = 9
    Closed = 0
    Disarmed = 8
    DoorLocked = 91
    DoorUnlocked = 90
    LightTurnedOff = 316
    LightTurnedOn = 315
    Opened = 15
    OpenedClosed = 100
    SwitchLevelChanged = 317
    ThermostatFanModeChanged = 120
    ThermostatModeChanged = 95
    ThermostatOffset = 105
    ThermostatSetPointChanged = 94

    # Unsupported
    Alarm = 1
    AccessControlDoorAccessGranted = 298
    AlarmCancelled = 238
    ArmingSupervisionFault = 48
    AuxiliaryPanic = 17
    AuxPanicPendingAlarm = 61
    AuxPanicSuspectedAlarm = 65
    BadLockUserCode = 93
    Bypassed = 13
    CommercialClosedOnTime = 127
    CommercialClosedUnexpectedly = 177
    CommercialEarlyClose = 125
    CommercialEarlyOpen = 122
    CommercialLateClose = 126
    CommercialLateOpen = 123
    CommercialOpenOnTime = 124
    DisarmingSupervisionFault = 47
    DoorAccessed = 92
    DoorAccessedDoubleSwipe = 236
    DoorBuzzedFromWebsite = 182
    DoorFailedAccess = 180
    DoorForcedOpen = 181
    DoorHeldOpen = 184
    EndOfBypass = 35
    ExitButtonPressed = 141
    FirePanic = 24
    GoogleSdmEvent = 346
    ImageSensorUpload = 99
    InAppAuxiliaryPanic = 201
    InAppFirePanic = 200
    InAppPolicePanic = 202
    InAppSilentPolicePanic = 203
    NetworkDhcpReservationsUpdated = 433
    NetworkDhcpSettingsUpdated = 432
    NetworkMapUpdated = 391
    NetworkPortForwardingUpdated = 434
    PackageDeliveryAlert = 363
    PackageRetrievalAlert = 364
    PendingAlarm = 62
    PolicePanic = 22
    PolicePanicSuspectedAlarm = 64
    RouterHostsUpdated = 450
    RouterProfilesUpdated = 451
    SilentPolicePanic = 73
    SilentPolicePanicSuspectedAlarm = 172
    SpeedTestResultsUpdated = 454
    SumpPumpAlertCriticalIssueMalfunction = 118
    SumpPumpAlertCriticalIssueOff = 117
    SumpPumpAlertIdle = 114
    SumpPumpAlertNormalOperation = 115
    SumpPumpAlertPossibleIssue = 116
    Tamper = 7
    UnknownCardFormatRead = 185
    VideoAnalytics2Detection = 302
    VideoAnalyticsDetection = 210
    VideoCameraTriggered = 71
    VideoEventTriggered = 76
    ViewedByCentralStation = 158
    WrongPinCode = 398

    # Undocumented
    UserLoggedIn = 55
    DoorLeftOpenRestoral = 103  # When door is closed after being left open. Paired with a door closed event.
    DoorLeftOpen = 101  # When door is left open for 30 minutes.


SUPPORTED_MONITORING_EVENT_TYPES = [
    EventType.ArmedAway,
    EventType.ArmedNight,
    EventType.ArmedStay,
    EventType.Closed,
    EventType.Disarmed,
    EventType.DoorLocked,
    EventType.DoorUnlocked,
    EventType.LightTurnedOff,
    EventType.LightTurnedOn,
    EventType.Opened,
    EventType.OpenedClosed,
    EventType.SwitchLevelChanged,
    EventType.ThermostatFanModeChanged,
    EventType.ThermostatModeChanged,
    EventType.ThermostatOffset,
    EventType.ThermostatSetPointChanged,
]
