"""Functions for communicating with Alarm.com over WebSockets."""

# noqa: T201

from __future__ import annotations

import json
import logging
from enum import Enum

import aiohttp
from aiohttp import ClientSession

from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.devices.garage_door import GarageDoor
from pyalarmdotcomajax.devices.gate import Gate
from pyalarmdotcomajax.devices.light import Light
from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.devices.registry import DeviceRegistry
from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.devices.thermostat import Thermostat
from pyalarmdotcomajax.devices.water_sensor import WaterSensor
from pyalarmdotcomajax.errors import AuthenticationFailed, DataFetchFailed
from pyalarmdotcomajax.websockets.handler.garage_door import GarageDoorWebSocketHandler
from pyalarmdotcomajax.websockets.handler.gate import GateWebSocketHandler
from pyalarmdotcomajax.websockets.handler.light import LightWebSocketHandler
from pyalarmdotcomajax.websockets.handler.partition import PartitionWebSocketHandler
from pyalarmdotcomajax.websockets.handler.sensor import SensorWebSocketHandler
from pyalarmdotcomajax.websockets.handler.thermostat import ThermostatWebSocketHandler
from pyalarmdotcomajax.websockets.handler.water_sensor import (
    WaterSensorWebSocketHandler,
)
from pyalarmdotcomajax.websockets.messages import (
    MonitoringEventMessage,
    process_raw_message,
)

log = logging.getLogger(__name__)


class WebSocketCloseCodes(Enum):
    """Enum for codes given by server on disconnect or reject."""

    Normal = 1000
    ServiceUnavailable = 1001
    TokenExpired = 1008


class WebSocketClient:
    """Class for communicating with Alarm.com over WebSockets."""

    WEBSOCKET_ENDPOINT_TEMPLATE = "wss://webskt.alarm.com:8443/?auth={}"
    WEBSOCKET_TOKEN_REQUEST_TEMPLATE = "{}web/api/websockets/token"  # noqa: S105

    def __init__(
        self,
        websession: ClientSession,
        ajax_headers: dict,
        device_registry: DeviceRegistry,
    ) -> None:
        """Initialize."""
        self._websession: ClientSession = websession
        self._ajax_headers: dict = ajax_headers
        self._device_registry: DeviceRegistry = device_registry
        self._ws_auth_token: str | None = None

    async def async_connect(self) -> None:
        """Connect to Alarm.com WebSocket."""

        # Get authentication token for websocket communication
        try:
            self._ws_auth_token = await self._async_get_websocket_token()
            if not self._ws_auth_token:
                raise AuthenticationFailed("async_connect(): Failed to get WebSocket authentication token.")
        except (DataFetchFailed, AuthenticationFailed) as err:
            raise AuthenticationFailed from err

        # Connect to websocket endpoint
        async with self._websession.ws_connect(
            self.WEBSOCKET_ENDPOINT_TEMPLATE.format(self._ws_auth_token), headers=self._ajax_headers, timeout=30
        ) as websocket:
            async for msg in websocket:
                # Message is JSON but encoded as text.
                if msg.type != aiohttp.WSMsgType.TEXT:
                    pass

                try:
                    await self._async_handle_message(json.loads(msg.data))
                except (TypeError, ValueError):
                    log.warning("Unable to parse message from Alarm.com: %s", msg.data)
                    # TODO: On failure, refresh everything synchronous HTTP endpoints.

    async def _async_handle_message(self, raw_message: dict) -> None:
        """Handle incoming message from Alarm.com."""

        log.debug(
            "\n====================[ WEBSOCKET MESSAGE: BEGIN ]====================\n"
            f"{json.dumps(raw_message, indent=4)}"
        )

        message = process_raw_message(raw_message, self._device_registry)

        if type(message) is MonitoringEventMessage:
            log.info(
                "Received Monitoring Event message. Messages of this type are ignored."
                f" [{message.device.name} ({message.device.id_})]"
            )
        else:
            match message.device:
                case Light():
                    await LightWebSocketHandler().process_message(message)
                case Sensor():
                    await SensorWebSocketHandler().process_message(message)
                case Partition():
                    await PartitionWebSocketHandler().process_message(message)
                case GarageDoor():
                    await GarageDoorWebSocketHandler().process_message(message)
                case Gate():
                    await GateWebSocketHandler().process_message(message)
                case Thermostat():
                    await ThermostatWebSocketHandler().process_message(message)
                case WaterSensor():
                    await WaterSensorWebSocketHandler().process_message(message)
                case _:
                    log.debug(
                        f"WebSocket support not yet implemented for {message.device.__class__.__name__.lower()}s."
                        f" [{message.device.name} ({message.device.id_})]"
                    )

        log.debug("\n====================[ WEBSOCKET MESSAGE: END ]====================")

    async def _async_get_websocket_token(self) -> str:
        """Get authentication token for websocket communication."""
        async with self._websession.get(
            url=self.WEBSOCKET_TOKEN_REQUEST_TEMPLATE.format(c.URL_BASE, ""),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await resp.json()

        if (
            ((errors := json_rsp.get("errors")) and len(errors) > 0)
            or ((validation_errors := json_rsp.get("validation_errors")) and len(validation_errors) > 0)
            or ((processing_errors := json_rsp.get("processingErrors")) and len(processing_errors) > 0)
            or ((token_value := json_rsp.get("value")) in [None, ""])
        ):
            log.debug(
                (
                    "async_get_websocket_token(): Received errors while requesting WebSocket authentication token."
                    " Response: %s"
                ),
                resp,
            )
            raise DataFetchFailed(
                "async_get_websocket_token(): Received errors while requesting WebSocket authentication token."
            )

        return str(token_value)
