"""Alarm.com websocket message utilities."""

from __future__ import annotations

import json
import logging
import urllib.parse
from datetime import datetime

from dateutil import parser

from pyalarmdotcomajax.devices.registry import AllDevices_t, DeviceRegistry
from pyalarmdotcomajax.exceptions import UnkonwnDevice, UnsupportedWebSocketMessage
from pyalarmdotcomajax.helpers import CastingMixin
from pyalarmdotcomajax.websockets.const import (
    SUPPORTED_MONITORING_EVENT_TYPES,
    SUPPORTED_PROPERY_CHANGE_TYPES,
    EventType,
    PropertyChangeType,
)

log = logging.getLogger(__name__)


def process_raw_message(message: dict, device_registry: DeviceRegistry) -> WebSocketMessage:
    """Create websocket message object from raw message."""

    try:
        device = device_registry.get(f"{message['UnitId']}-{message['DeviceId']}")
    except UnkonwnDevice:
        # This tends to happen for devices on pyalarmdotcomajax's blacklist.
        log.debug(
            "Got a message for unknown device"
            f" {message['UnitId']}-{message['DeviceId']}:\n{json.dumps(message, indent=4)}"
        )

    try:
        if {"FenceId", "IsInsideNow"} <= set(message.keys()):
            # Geofence Event (Not Yet Supported)
            pass
        elif {"EventType", "EventValue", "QstringForExtraData"} <= set(message.keys()):
            # Event
            log.debug("WebSocket Message Type: Event")
            return EventMessage(message, device)
        elif {"EventType", "CorrelatedId"} <= set(message.keys()):
            # Monitoring Event
            log.debug("WebSocket Message Type: Monitoring Event")
            return MonitoringEventMessage(message, device)
        elif {"Property", "PropertyValue"} <= set(message.keys()):
            # Property Change
            log.debug("WebSocket Message Type: Property Change")
            return PropertyChangeMessage(message, device)
        elif {"NewState", "FlagMask"} <= set(message.keys()):
            # State Change
            log.debug("WebSocket Message Type: State Change")
            return StatusChangeMessage(message, device)
    except KeyError:
        log.exception(f"Failed to parse websocket message: {message}")

    raise UnsupportedWebSocketMessage(message)


class WebSocketMessage(CastingMixin):
    """Alarm.com websocket message base class."""

    def __init__(self, message: dict, device: AllDevices_t):
        """Initialize."""
        self.id_: str = f"{message.get('UnitId', '')!s}-{message.get('DeviceId', '')!s}"
        self.device: AllDevices_t = device


class EventMessage(WebSocketMessage):
    """Alarm.com event websocket message class."""

    def __init__(self, message: dict, device: AllDevices_t):
        """Initialize."""
        super().__init__(message, device)
        self.date: datetime | None = parser.parse(message.get("EventDateUtc", ""))
        self.value = self._safe_float_from_dict(message, "EventValue")
        self.extra_data: dict | None = dict(
            urllib.parse.parse_qsl(self._safe_str_from_dict(message, "QstringForExtraData"))
        )
        self.event_type: EventType | None = self._safe_special_from_dict(message, "EventType", EventType)
        self.event_type_id: int | None = self._safe_int_from_dict(message, "EventType")

    def is_supported(self) -> bool:
        """Return true if the event type is supported."""
        return self.event_type in SUPPORTED_MONITORING_EVENT_TYPES

    # EXTRA DATA CONTENTS

    # LOCKS
    # Changed by Keypad: {'ew_contact_id': '000000000', 'lockedByKeypad': 'true', 'ew': 'User Full Name', 'ew_group_id': '00'}
    # Changed by Z-Wave: {'unlock_method': 'ZwaveUnlock', 'ew': None} and {'lock_method': 'ZwaveLock', 'ew': None}
    # Changed by Key/Knob: {'lock_method': 'ManualLock', 'ew': None} and {'unlock_method': 'ManualUnlock', 'ew': None}

    # SENSORS OPEN/CLOSE: {'openClosedStatusWord': 'open'}
    # PANEL USER LOGS IN ONLINE: {'ln': 'username', 'ip': '000.000.000.000', 'src': '1', 'mrid': None}
    # THERMOSTAT: {'tempC': 2333.00} (for 7400 F value)


class MonitoringEventMessage(WebSocketMessage):
    """Alarm.com monitoring event websocket message class."""

    def __init__(self, message: dict, device: AllDevices_t):
        """Initialize."""
        super().__init__(message, device)
        self.date: datetime | None = parser.parse(message.get("EventDateUtc", ""))
        self.value = self._safe_float_from_dict(message, "EventValue")
        self.correlated_id: int | None = self._safe_int_from_dict(message, "CorrelatedId")
        self.event_type: EventType | None = self._safe_special_from_dict(message, "EventType", EventType)
        self.event_type_id: int | None = self._safe_int_from_dict(message, "EventType")

    def is_supported(self) -> bool:
        """Return true if the event type is supported."""
        return self.event_type in SUPPORTED_MONITORING_EVENT_TYPES


class PropertyChangeMessage(WebSocketMessage):
    """Alarm.com property change websocket message class."""

    def __init__(self, message: dict, device: AllDevices_t):
        """Initialize."""
        super().__init__(message, device)
        self.change_date: datetime = parser.parse(message.get("ChangeDateUtc", ""))
        self.reported_date: datetime = parser.parse(message.get("ReportedDateUtc", ""))
        self.extra_data: dict | None = dict(
            urllib.parse.parse_qsl(self._safe_str_from_dict(message, "QstringForExtraData"))
        )
        self.value: int | None = self._safe_int_from_dict(message, "PropertyValue")
        self.property: PropertyChangeType | None = self._safe_special_from_dict(
            message, "Property", PropertyChangeType
        )

    def is_supported(self) -> bool:
        """Return true if the property change type is supported."""

        return self.property in SUPPORTED_PROPERY_CHANGE_TYPES


class StatusChangeMessage(WebSocketMessage):
    """Alarm.com status update websocket message class."""

    def __init__(self, message: dict, device: AllDevices_t):
        """Initialize."""
        super().__init__(message, device)
        self.date: datetime = parser.parse(message.get("EventDateUtc", ""))
        self.flag_mask: str | None = message.get("FlagMask")
        self.new_state: int

        self.new_state = message["NewState"]
