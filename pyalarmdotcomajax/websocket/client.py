"""Event controller."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal, NoReturn

import aiohttp

from pyalarmdotcomajax.const import API_URL_BASE
from pyalarmdotcomajax.events import EventBrokerMessage, EventBrokerTopic
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    NotInitialized,
    OtpRequired,
    ServiceUnavailable,
    SessionExpired,
    UnexpectedResponse,
)
from pyalarmdotcomajax.websocket.messages import (
    UNDEFINED,
    BaseWSMessage,
    EventWSMessage,
    PropertyChangeWSMessage,
    ResourceEventType,
    ResourcePropertyChangeType,
    WebSocketMessageTester,
)

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge


ALL_TOKEN = "*"  # noqa: S105
ALL_TOKEN_T = Literal["*"]


KEEP_ALIVE_SIGNAL_INTERVAL_S = 60
MAX_RECONNECT_WAIT_S = 30 * 60
DEFAULT_SIGNALS_PER_SESSION_REFRESH = 1
MAX_CONNECTION_FAILURES = 25


log = logging.getLogger(__name__)


class WebSocketState(Enum):
    """Enum with possible Events."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    DEAD = "dead"
    WAITING = "waiting"

    # Only for emit
    RECONNECTED = "reconnected"


@dataclass(kw_only=True)
class RawUpdatedResourceMessage(EventBrokerMessage):
    """Message class for updated resources."""

    topic: EventBrokerTopic = EventBrokerTopic.RAW_RESOURCE_EVENT
    ws_message: BaseWSMessage


@dataclass(kw_only=True)
class ConnectionEvent(EventBrokerMessage):
    """Message class for updated resources."""

    topic: EventBrokerTopic = EventBrokerTopic.CONNECTION_EVENT
    current_state: WebSocketState
    next_attempt_s: int | None = None


@dataclass
class SupportedResourceEvents:
    """Supported WebSocket Notifications."""

    state_change: bool = False
    geofence_crossing: bool = False
    events: list[ResourceEventType | ALL_TOKEN_T] = field(default_factory=list)
    property_changes: list[ResourcePropertyChangeType | ALL_TOKEN_T] = field(default_factory=list)


class WebSocketClient:
    """Control WebSocket connection and distribute messages."""

    def __init__(self, bridge: AlarmBridge) -> None:
        """Initialize authentication controller."""
        self._bridge = bridge

        self._token: str | None = None
        self._ws_endpoint: str | None = None

        self._state = WebSocketState.DISCONNECTED

        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: list[asyncio.Task] = []

        self._last_session_refresh: datetime | None = None
        self._session_refresh_interval_ms: int | None = None
        self._keep_alive_url: str | None = None
        self._event_history: deque = deque(maxlen=25)

        self._initialized = False

    @property
    def connected(self) -> bool:
        """Whether client is connected to server."""

        return self.state == WebSocketState.CONNECTED

    @property
    def state(self) -> WebSocketState:
        """Return connection state."""

        return self._state

    @property
    def last_events(self) -> list[dict]:
        """Return a list with the previous X messages."""

        return list(self._event_history)

    async def initialize(self) -> None:
        """
        Start listening for events.

        Connection will be auto-reconnected if it gets lost.
        """

        if not self._bridge.initialized:
            raise NotInitialized

        if self._initialized:
            return

        def emergency_stop(task: asyncio.Task) -> None:
            """Stop all background tasks and state reason."""

            if task.cancelled():
                log.debug(f"WebSocket client task {task.get_name()} was killed.")
            else:
                log.error(f"WebSocket client ran into an error with the {task.get_name()} task. Killing siblings.")
                self.stop(WebSocketState.DEAD)

        if len(self._background_tasks) > 0:
            raise RuntimeError("Already initialized")

        self._background_tasks.append(asyncio.create_task(self._event_reader(), name="Event Reader"))
        self._background_tasks.append(asyncio.create_task(self._event_processor(), name="Event Processor"))
        self._background_tasks.append(asyncio.create_task(self._keep_alive(), name="Keep Alive"))

        for task in self._background_tasks:
            task.add_done_callback(emergency_stop)

        self._initialized = True

    def stop(self, state: WebSocketState = WebSocketState.DISCONNECTED) -> None:
        """Stop listening for events."""

        self._set_state(state)

        for task in self._background_tasks:
            task.cancel()

        self._background_tasks = []

        self._initialized = False

    async def _authenticate(self) -> None:
        """Get authentication token for websocket endpoint."""

        log.info("Getting WebSocket token.")

        try:
            if not await self._bridge.is_logged_in():
                log.debug("Primary session expired. Reauthenticating to Alarm.com.")
                await self._bridge.login()
        except (ServiceUnavailable, UnexpectedResponse):
            log.debug("Failed to connect to Alarm.com when authenticating. Try again later.")
            return

        self._token = None

        try:
            response = await self._bridge.get(path="websockets/token", id=None, mini_response=True)
        except SessionExpired:
            log.error("Detected session timeout, but session was just checked.")
            raise

        try:
            self._ws_endpoint = response.metadata["endpoint"]
        except KeyError as err:
            raise UnexpectedResponse("Failed to get WebSocket endpoint.") from err

        # Set token only after we have a valid websocket endpoint.
        self._token = response.value

    def emit_ws_state(self, state: WebSocketState, next_attempt_s: int | None = None) -> None:
        """Emit connection event to all listeners."""

        self._bridge.events.publish(ConnectionEvent(current_state=state, next_attempt_s=next_attempt_s))

    def emit_resource(self, data: BaseWSMessage) -> None:
        """Emit resource event to all listeners."""

        self._bridge.events.publish(RawUpdatedResourceMessage(ws_message=data))

    async def _event_reader(self) -> NoReturn:
        """Maintain connection with server and read events from stream."""

        self._set_state(WebSocketState.CONNECTING)
        connect_attempts = 0

        while True:
            connect_attempts += 1

            try:
                # Get a new token on the first connect attempt and on every 10 reconnect attempts.
                if (not self._token) or connect_attempts == 1 or connect_attempts % 10 == 0:
                    await self._authenticate()

                async with self._bridge.ws_connect(f"{self._ws_endpoint}/?f=1&auth={self._token}") as websocket:
                    self._set_state(
                        WebSocketState.CONNECTED if connect_attempts == 1 else WebSocketState.RECONNECTED,
                    )
                    connect_attempts = 1

                    log.info("Connected to WebSocket")

                    async for msg in websocket:
                        if msg.type == aiohttp.WSMsgType.CLOSED:
                            log.info(
                                "aiohttp WebSocket connection closed: Code: %s, Message: '%s'", msg.data, msg.extra
                            )
                            continue

                        if msg.type == aiohttp.WSMsgType.ERROR:
                            log.info("aiohttp WebSocket error: '%s'", msg.data)
                            continue

                        if msg.type != aiohttp.WSMsgType.TEXT:
                            log.debug("Got non-text WebSocket message: '%s'", msg.data)
                            continue

                        self._event_queue.put_nowait(msg.data)
                        self._event_history.append(msg.data)

            except OtpRequired:
                log.error(
                    "Server requested OTP when attempting to keep session alive. This was most likely caused by an issue extracting the MFA token during sign-in."
                )
                raise
            except (AuthenticationFailed, SessionExpired):
                # Token request failed.
                log.debug("Failed to authenticate WebSocket connection. This is likely due to a session timeout.")
                self._token = None
            except (
                TimeoutError,
                aiohttp.ClientError,
                UnexpectedResponse,
                aiohttp.ClientConnectionError,
            ) as err:
                log.debug(f"Encountered WebSocket error: {err}\nAttempting to recover.")
                if getattr(err, "status", None) == 401:
                    log.error("Failed to authenticate WebSocket connection.")
                    self._token = None
            except Exception as err:
                # for debugging purpose only
                log.exception("Fatal Error")
                raise err  # noqa: TRY201

            if connect_attempts >= MAX_CONNECTION_FAILURES:
                self.stop()

            # Webapp uses a 15 second minimum
            reconnect_wait = min(15 * connect_attempts, MAX_RECONNECT_WAIT_S)

            log.debug(
                "WebSockets Disconnected" " - Reconnect will be attempted in %s seconds",
                reconnect_wait,
            )

            self._set_state(WebSocketState.DISCONNECTED, reconnect_wait)

            # every 10 failed connect attempts log warning
            if connect_attempts % 10 == 0:
                log.warning(
                    "%s attempts to (re)connect Alarm.com WebSocket endpoint failed.",
                    connect_attempts,
                )

            self._set_state(WebSocketState.WAITING)

            await asyncio.sleep(reconnect_wait)

    async def _event_processor(self) -> NoReturn:
        """Process incoming events."""

        while True:
            try:
                msg_json: str = str(await self._event_queue.get())

                msg_tester = WebSocketMessageTester.from_json(msg_json)

                converted_message: BaseWSMessage | None = None

                log.debug(f"Received WebSocket Message: {msg_json}")

                # Determine and set message type class.
                # "Passed" message types seem to be unused by Alarm.com's webapp. The same actions
                # are instead handled via event messages.

                if UNDEFINED not in [msg_tester.fence_id, msg_tester.is_inside_now]:
                    # converted_message = GeofenceCrossingWSMessage.from_json(msg_json)
                    continue

                if UNDEFINED not in [msg_tester.event_type, msg_tester.correlated_event_id]:
                    # converted_message = MonitoringEventWSMessage.from_json(msg_json)
                    continue

                if UNDEFINED not in [msg_tester.new_state, msg_tester.flag_mask]:
                    # converted_message = StatusUpdateWSMessage.from_json(msg_json)
                    continue

                if UNDEFINED not in [
                    msg_tester.event_type,
                    msg_tester.event_value,
                    msg_tester.qstring_for_extra_data,
                ]:
                    converted_message = EventWSMessage.from_json(msg_json)

                elif UNDEFINED not in [msg_tester.property_, msg_tester.property_value]:
                    converted_message = PropertyChangeWSMessage.from_json(msg_json)

                log.debug(f"WebSocket message type identified as {converted_message.__class__.__name__}")

                if converted_message:
                    self.emit_resource(converted_message)
                else:
                    log.warning("Unprocessable message received: %s", json.loads(msg_json))

            except Exception:
                log.exception("Failed to convert message: %s", json.loads(msg_json))

    def _set_state(self, state: WebSocketState, reconnect_wait: int | None = None) -> None:
        """Set WS client state and emit message only if state has changed."""

        if self._state != state:
            self._state = WebSocketState.CONNECTED if state == WebSocketState.RECONNECTED else state
            self.emit_ws_state(state, reconnect_wait)

    ################################
    # SESSION KEEP ALIVE FUNCTIONS #
    ################################

    async def _reload_session_context(self) -> None:
        """Check if we are still logged in."""

        log.info("Reloading session context.")

        url = f"{API_URL_BASE}identities/{self._bridge.auth_controller.profile_id}/reloadContext"
        payload = {"included": [], "meta": {"transformer_version": "1.1"}}

        async with self._bridge.create_request("post", url, json=payload, raise_for_status=True) as rsp:
            text_rsp = await rsp.text()

            if rsp.status >= 400:
                raise UnexpectedResponse(f"Failed to reload session context. Response: {text_rsp}")

        log.debug("Reloaded context. Fetching new token...")

        await self._authenticate()

    async def _keep_alive(self) -> NoReturn:
        """
        Keep session alive.

        Alarm.com's webapp uses the keep alive to handle session timeouts. We'll use the event reader to do that, instead.
        """

        # Determine number of keep_alives to send between session refreshes.
        session_refresh_interval_ms = self._bridge.auth_controller.session_refresh_interval_ms
        session_refresh_interval = max(
            int(session_refresh_interval_ms / (KEEP_ALIVE_SIGNAL_INTERVAL_S * 1000)),
            DEFAULT_SIGNALS_PER_SESSION_REFRESH,
        )

        log.info(f"Session refresh interval: {session_refresh_interval_ms} ms / {session_refresh_interval} pings")

        signals_sent = 0

        while True:
            await asyncio.sleep(KEEP_ALIVE_SIGNAL_INTERVAL_S)

            # Don't send requests if websocket client is disconnected.
            if self.state != WebSocketState.CONNECTED:
                log.debug("Skipping keep alive.")
                signals_sent = 0
                continue

            log.debug("Sending keep alive.")

            try:
                if signals_sent >= session_refresh_interval - 1:
                    signals_sent = 0
                    await self._reload_session_context()
                if self._bridge.auth_controller.enable_keep_alive and not await self._bridge.is_logged_in():
                    log.info("[Keep Alive] Detected expired user session.")
            except Exception as err:
                # All connection error handling managed by event reader.
                log.debug(f"Error while sending keep alive: {err}")

            signals_sent += 1
