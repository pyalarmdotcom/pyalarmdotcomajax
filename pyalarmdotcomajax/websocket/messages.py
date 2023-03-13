"""Alarm.com websocket message utilities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from dateutil import parser

from pyalarmdotcomajax.helpers import CastingMixin


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


class MonitoringEventType(Enum):
    """Enum for monitoring event types."""

    # Supported
    ArmedAway = 10
    ArmedNight = 113
    ArmedStay = 9
    Closed = 0
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

    # Not Supported
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


SUPPORTED_MONITORING_EVENT_TYPES = [
    MonitoringEventType.ArmedAway,
    MonitoringEventType.ArmedNight,
    MonitoringEventType.ArmedStay,
    MonitoringEventType.Closed,
    MonitoringEventType.DoorLocked,
    MonitoringEventType.DoorUnlocked,
    MonitoringEventType.ImageSensorUpload,
    MonitoringEventType.LightTurnedOff,
    MonitoringEventType.LightTurnedOn,
    MonitoringEventType.Opened,
    MonitoringEventType.OpenedClosed,
    MonitoringEventType.SupervisionFaultArming,
    MonitoringEventType.SupervisionFaultDisarming,
    MonitoringEventType.SwitchLevelChanged,
    MonitoringEventType.ThermostatFanModeChanged,
    MonitoringEventType.ThermostatModeChanged,
    MonitoringEventType.ThermostatOffset,
    MonitoringEventType.ThermostatSetPointChanged,
]


class WebSocketMessage(CastingMixin):
    """Alarm.com websocket message base class."""

    def __init__(self, message: dict):
        """Initialize."""
        self.id_: str = (
            f"{str(message.get('UnitId', ''))}-{str(message.get('DeviceId', ''))}"
        )


class MonitoringMessage(WebSocketMessage):
    """Alarm.com monitoring event websocket message class."""

    def __init__(self, message: dict):
        """Initialize."""
        super().__init__(message)
        self.type_: str = message.get("eventType", "")
        self.date: datetime | None = parser.parse(message.get("EventDateUtc", ""))
        self.value = self._safe_float_from_dict(message, "EventValue")
        self.extra_data: str | None = self._safe_str_from_dict(
            message, "QstringForExtraData"
        )
        self.correlated_id: int | None = self._safe_int_from_dict(
            message, "CorrelatedId"
        )
        self.event_type: MonitoringEventType | None = self._safe_special_from_dict(
            message, "EventType", MonitoringEventType
        )

    def is_supported(self) -> bool:
        """Return true if the event type is supported."""
        return self.event_type in SUPPORTED_MONITORING_EVENT_TYPES


class PropertyChangeMessage(WebSocketMessage):
    """Alarm.com property change websocket message class."""

    def __init__(self, message: dict):
        """Initialize."""
        super().__init__(message)
        self.change_date: datetime = parser.parse(message.get("ChangeDateUtc", ""))
        self.reported_date: datetime = parser.parse(message.get("ReportedDateUtc", ""))
        self.extra_data: str | None = self._safe_str_from_dict(
            message, "QstringForExtraData"
        )
        self.value: int | None = self._safe_int_from_dict(message, "PropertyValue")
        self.property: PropertyChangeType | None = self._safe_special_from_dict(
            message, "Property", PropertyChangeType
        )

    def is_supported(self) -> bool:
        """Return true if the property change type is supported."""

        return self.property in SUPPORTED_PROPERY_CHANGE_TYPES


class StateChangeMessage(WebSocketMessage):
    """Alarm.com status update websocket message class."""

    def __init__(self, message: dict):
        """Initialize."""
        super().__init__(message)
        self.date: datetime = parser.parse(message.get("EventDateUtc", ""))
        self.new_state: datetime = parser.parse(message.get("NewState", ""))
        self.flag_mask: str | None = message.get("FlagMask")
