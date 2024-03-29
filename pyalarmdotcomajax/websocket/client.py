"""Event controller."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from collections.abc import Callable, KeysView
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, NoReturn

import aiohttp

from pyalarmdotcomajax.const import API_URL_BASE
from pyalarmdotcomajax.exceptions import (
    AlarmdotcomException,
    AuthenticationFailed,
    OtpRequired,
    ServiceUnavailable,
    SessionTimeout,
    UnexpectedResponse,
)
from pyalarmdotcomajax.websocket.messages import (
    UNDEFINED,
    BaseWSMessage,
    EventWSMessage,
    GeofenceCrossingWSMessage,
    MonitoringEventWSMessage,
    PropertyChangeWSMessage,
    ResourceEventType,
    ResourcePropertyChangeType,
    StatusUpdateWSMessage,
    WebSocketMessageTester,
)

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge


ALL_TOKEN = "*"  # noqa: S105
ALL_TOKEN_T = Literal["*"]


KEEP_ALIVE_SIGNAL_INTERVAL_S = 60
DEFAULT_SIGNALS_PER_SESSION_REFRESH = 1
MAX_KEEP_ALIVE_FAILURES = 10


log = logging.getLogger(__name__)


class WebSocketState(Enum):
    """Enum with possible Events."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    DEAD = "dead"

    # Only for emit
    RECONNECTED = "reconnected"


class WebSocketNotificationType(Enum):
    """Enum with possible Events."""

    RESOURCE_EVENT = "RESOURCE_EVENT"
    CONNECTION_EVENT = "CONNECTION_EVENT"


@dataclass
class SupportedResourceEvents:
    """Supported WebSocket Notifications."""

    state_change: bool = False
    geofence_crossing: bool = False
    events: list[ResourceEventType | ALL_TOKEN_T] = field(default_factory=list)
    property_changes: list[ResourcePropertyChangeType | ALL_TOKEN_T] = field(default_factory=list)


WebSocketResourceEventCallBackT = Callable[[BaseWSMessage], Any]
WebSocketConnectionEventCallBackT = Callable[[WebSocketState, int | None], Any]

WebSocketConnectionEventSubscriptionT = WebSocketConnectionEventCallBackT
WebSocketResourceEventSubscriptionT = tuple[
    WebSocketResourceEventCallBackT, SupportedResourceEvents, list[str] | KeysView[str]
]


class WebSocketClient:
    """Control WebSocket connection and distribute messages."""

    def __init__(self, bridge: AlarmBridge) -> None:
        """Initialize authentication controller."""
        self._bridge = bridge

        self._token: str | None = None
        self._ws_endpoint: str | None = None

        self._state = WebSocketState.DISCONNECTED

        self._connection_subscribers: list[WebSocketConnectionEventSubscriptionT] = []
        self._resource_subscribers: list[WebSocketResourceEventSubscriptionT] = []

        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: list[asyncio.Task] = []

        self._last_session_refresh: datetime | None = None
        self._session_refresh_interval_ms: int | None = None
        self._keep_alive_url: str | None = None
        self._event_history: deque = deque(maxlen=25)

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

    def stop(self, state: WebSocketState = WebSocketState.DISCONNECTED) -> None:
        """Stop listening for events."""

        self._set_state(state)

        for task in self._background_tasks:
            task.cancel()

        self._background_tasks = []

    async def _authenticate(self) -> None:
        """Get authentication token for websocket endpoint."""

        log.info("Getting WebSocket token.")

        try:
            response = await self._bridge.get(path="websockets/token", id=None, mini_response=True)
        except AuthenticationFailed:
            log.info("Detected session timeout. Logging back in.")
            await self._bridge.login()

        self._token = response.value

        try:
            self._ws_endpoint = response.metadata["endpoint"]
        except KeyError as err:
            raise UnexpectedResponse("Failed to get WebSocket endpoint.") from err

    def subscribe_resource(
        self,
        callback: WebSocketResourceEventCallBackT,
        resource_event_filter: SupportedResourceEvents,
        resource_ids: list[str] | KeysView[str] | None = None,
    ) -> Callable:
        """Subscribe to resource events."""
        if not resource_event_filter:
            raise ValueError("Resource event subscriptions require resource_event_filter argument.")

        # log.debug(f"Got subscription to WebSocket resource events: {resource_event_filter, callback}")

        subscription = (callback, resource_event_filter, resource_ids if resource_ids else [ALL_TOKEN])

        def unsubscribe() -> None:
            self._resource_subscribers.remove(subscription)

        self._resource_subscribers.append(subscription)
        return unsubscribe

    def subscribe_connection(
        self,
        callback: WebSocketConnectionEventCallBackT,
    ) -> Callable:
        """Subscribe to connection events."""
        subscription = callback

        def unsubscribe() -> None:
            self._connection_subscribers.remove(subscription)

        self._connection_subscribers.append(subscription)
        return unsubscribe

    def emit_ws_state(self, state: WebSocketState, next_attempt_s: int | None = None) -> None:
        """Emit connection event to all listeners."""
        for callback in self._connection_subscribers:
            if asyncio.iscoroutinefunction(callback):
                self._background_tasks.append(asyncio.create_task(callback(state, next_attempt_s)))
            else:
                callback(state, next_attempt_s)

    def emit_resource(self, data: BaseWSMessage) -> None:
        """Emit resource event to all listeners."""

        for callback, supported_resource_events, resource_ids in self._resource_subscribers:
            if any(x in resource_ids for x in (ALL_TOKEN, data.device_id)):
                if isinstance(data, EventWSMessage | MonitoringEventWSMessage) and not any(
                    x in supported_resource_events.events for x in (data.subtype, ALL_TOKEN)
                ):
                    continue
                if isinstance(data, PropertyChangeWSMessage) and not any(
                    x in supported_resource_events.property_changes for x in (data.subtype, ALL_TOKEN)
                ):
                    continue
                if isinstance(data, StatusUpdateWSMessage) and not supported_resource_events.state_change:
                    continue
                if isinstance(data, GeofenceCrossingWSMessage) and not supported_resource_events.geofence_crossing:
                    continue

            if asyncio.iscoroutinefunction(callback):
                self._background_tasks.append(asyncio.create_task(callback(data)))
            else:
                callback(data)

    async def _event_reader(self) -> NoReturn:
        """Maintain connection with server and read events from stream."""

        self._set_state(WebSocketState.CONNECTING)
        connect_attempts = 0

        while True:
            connect_attempts += 1

            try:
                try:
                    # Get a new token on the first connect attempt and on every 10 reconnect attempts.
                    if connect_attempts == 1 or connect_attempts % 10 == 0:
                        await self._authenticate()
                except OtpRequired:
                    log.error(
                        "Server requested OTP when attempting to keep session alive. This was most likely caused by an issue extracting the MFA token during sign-in."
                    )
                    raise AuthenticationFailed
                except AuthenticationFailed:
                    log.error(
                        "Failed to authenticate WebSocket connection. This is likely due to a session timeout."
                    )
                    raise

                async with self._bridge.ws_connect(f"{self._ws_endpoint}/?auth={self._token}") as websocket:
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

            except (
                TimeoutError,
                aiohttp.ClientError,
                UnexpectedResponse,
                ServiceUnavailable,
                SessionTimeout,
            ) as err:
                # pass expected connection errors because we will auto retry
                status = getattr(err, "status", None)
                if status == 403:
                    raise AuthenticationFailed from err
                log.debug(f"Recoverable WebSocket error: {err}")
            except Exception as err:
                # for debugging purpose only
                log.exception("[Event Reader] Fatal Error")
                raise err  # noqa: TRY201

            # Use the same 5 second minimum used by the webapp.
            reconnect_wait = min(max(2 * connect_attempts, 10), 50)

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

            self._set_state(WebSocketState.CONNECTING)

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
                # "Passed" message types seem to be disused by Alarm.com's webapp. The same actions
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
            self._state = state
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

            log.debug("Sending keep alive.")

            # if self.state != WebSocketState.CONNECTED:
            #     signals_sent = 0
            #     continue

            try:
                if signals_sent >= session_refresh_interval - 1:
                    signals_sent = 0
                    await self._reload_session_context()
                if self._bridge.auth_controller.enable_keep_alive and not await self._bridge.is_logged_in():
                    log.info("[Keep Alive] Detected expired user session.")
            except (TimeoutError, aiohttp.ClientError, SessionTimeout, AlarmdotcomException) as err:
                log.debug(f"Error while sending keep alive: {err}")

            signals_sent += 1
