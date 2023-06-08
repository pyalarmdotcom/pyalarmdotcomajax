"""Functions for communicating with Alarm.com over WebSockets."""


from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from enum import Enum

import aiohttp
from aiohttp import ClientSession

from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.devices.garage_door import GarageDoor
from pyalarmdotcomajax.devices.gate import Gate
from pyalarmdotcomajax.devices.light import Light
from pyalarmdotcomajax.devices.lock import Lock
from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.devices.registry import DeviceRegistry
from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.devices.thermostat import Thermostat
from pyalarmdotcomajax.devices.water_sensor import WaterSensor
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    UnexpectedResponse,
)
from pyalarmdotcomajax.websockets.handler.garage_door import GarageDoorWebSocketHandler
from pyalarmdotcomajax.websockets.handler.gate import GateWebSocketHandler
from pyalarmdotcomajax.websockets.handler.light import LightWebSocketHandler
from pyalarmdotcomajax.websockets.handler.lock import LockWebSocketHandler
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


class WebSocketState(Enum):
    """Websocket state."""

    DISCONNECTED = "disconnected"
    RUNNING = "running"
    STARTING = "starting"
    STOPPED = "stopped"


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
        ws_state_callback: Callable[[WebSocketState], None] | None = None,
    ) -> None:
        """Initialize."""
        self._websession: ClientSession = websession
        self._ajax_headers: dict = ajax_headers
        self._device_registry: DeviceRegistry = device_registry
        self._ws_auth_token: str | None = None
        self._ws_connection: aiohttp.ClientWebSocketResponse | None = None
        self._state = WebSocketState.STOPPED
        self._ws_state_callback = ws_state_callback
        self._loop = asyncio.get_running_loop()

    @property
    def state(self) -> WebSocketState:
        """State of websocket."""
        return self._state

    @state.setter
    def state(self, value: WebSocketState) -> None:
        """Set state of websocket."""
        self._state = value
        log.debug("Websocket %s", value)

        if self._ws_state_callback:
            self._ws_state_callback(value)

    async def _connect(self) -> None:
        """Connect to Alarm.com WebSocket."""

        # Get authentication token for websocket communication
        try:
            self._ws_auth_token = await self._async_get_websocket_token()
        except (UnexpectedResponse, AuthenticationFailed) as err:
            raise AuthenticationFailed from err

        if not self._ws_auth_token:
            raise AuthenticationFailed("async_connect(): Failed to get WebSocket authentication token.")

        try:
            # Connect to websocket endpoint
            async with self._websession.ws_connect(
                self.WEBSOCKET_ENDPOINT_TEMPLATE.format(self._ws_auth_token),
                headers=self._ajax_headers,
                timeout=30,
            ) as websocket:
                self.state = WebSocketState.RUNNING

                async for msg in websocket:
                    if self.state == WebSocketState.STOPPED:
                        break

                    # Message is JSON but encoded as text.
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        pass
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        log.warning("AIOHTTP websocket connection closed")
                        break

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        log.exception("AIOHTTP websocket error: '%s'", msg.data)
                        break

                    try:
                        await self._async_handle_message(json.loads(msg.data))
                    except (TypeError, ValueError):
                        log.warning("Unable to parse message from Alarm.com: %s", msg.data)
                        # TODO: On failure, refresh everything synchronous HTTP endpoints.
                        pass

        except aiohttp.ClientConnectorError:
            if self.state != WebSocketState.STOPPED:
                log.exception("WebSocket client connection error")
                self.state = WebSocketState.DISCONNECTED

        except Exception:
            if self.state != WebSocketState.STOPPED:
                log.exception("Unexpected WebSocket error")
                self.state = WebSocketState.DISCONNECTED

        else:
            if self.state != WebSocketState.STOPPED:
                self.state = WebSocketState.DISCONNECTED

    def start(self) -> None:
        """Start websocket and update its state."""
        if self.state != WebSocketState.RUNNING:
            self.state = WebSocketState.STARTING
            self._loop.create_task(self._connect())

    def stop(self) -> None:
        """Close websocket connection."""
        self.state = WebSocketState.STOPPED

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
                case Lock():
                    await LockWebSocketHandler().process_message(message)
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
            raise UnexpectedResponse(
                "async_get_websocket_token(): Received errors while requesting WebSocket authentication token."
            )

        return str(token_value)
