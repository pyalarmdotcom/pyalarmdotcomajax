"""pyalarmdotcomajax - A Python library for interacting with Alarm.com's API."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from collections.abc import AsyncIterator, Callable
from types import TracebackType
from typing import Any, TypeVar, overload

import aiohttp
from mashumaro.exceptions import MissingField, SuitableVariantNotFoundError

from pyalarmdotcomajax.const import REQUEST_RETRY_LIMIT, SUBMIT_RETRY_LIMIT
from pyalarmdotcomajax.controllers import EventType
from pyalarmdotcomajax.controllers.auth import AuthenticationController
from pyalarmdotcomajax.controllers.base import EventCallBackType
from pyalarmdotcomajax.controllers.cameras import CameraController
from pyalarmdotcomajax.controllers.device_catalogs import DeviceCatalogController
from pyalarmdotcomajax.controllers.garage_doors import GarageDoorController
from pyalarmdotcomajax.controllers.gates import GateController
from pyalarmdotcomajax.controllers.image_sensors import ImageSensorController, ImageSensorImageController
from pyalarmdotcomajax.controllers.lights import LightController
from pyalarmdotcomajax.controllers.locks import LockController
from pyalarmdotcomajax.controllers.partitions import PartitionController
from pyalarmdotcomajax.controllers.sensors import SensorController
from pyalarmdotcomajax.controllers.systems import SystemController
from pyalarmdotcomajax.controllers.thermostats import ThermostatController
from pyalarmdotcomajax.controllers.trouble_conditions import TroubleConditionController
from pyalarmdotcomajax.controllers.users import (
    AvailableSystemsController,
)
from pyalarmdotcomajax.controllers.water_sensors import WaterSensorController
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    NotAuthorized,
    NotInitialized,
    ServiceUnavailable,
    UnexpectedResponse,
)
from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.models.jsonapi import (
    JsonApiBaseElement,
    JsonApiFailureResponse,
    JsonApiInfoResponse,
    JsonApiSuccessResponse,
)
from pyalarmdotcomajax.websocket.client import WebSocketClient, WebSocketState

__version__ = "0.0.1"


logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
# log.setLevel(5)


class AlarmBridge:
    """Alarm.com bridge."""

    def __init__(self, username: str, password: str, mfa_token: str | None = None) -> None:
        """Initialize alarm bridge."""

        self._initialized = False

        # Session
        self._websession: aiohttp.ClientSession | None = None
        self._ajax_key: str | None = None

        # Meta Controllers
        self._auth_controller = AuthenticationController(self, username, password, mfa_token)
        self._available_device_catalogs = AvailableSystemsController(self)
        self._systems = SystemController(self)
        self._trouble_conditions = TroubleConditionController(self)
        self._ws_controller = WebSocketClient(self)

        # Device Controllers
        self._device_catalogs = DeviceCatalogController(self)
        self._cameras = CameraController(self, self._device_catalogs)
        self._garage_doors = GarageDoorController(self, self._device_catalogs)
        self._lights = LightController(self, self._device_catalogs)
        self._gates = GateController(self, self._device_catalogs)
        self._locks = LockController(self, self._device_catalogs)
        self._partitions = PartitionController(self, self._device_catalogs)
        self._sensors = SensorController(self, self._device_catalogs)
        self._thermostats = ThermostatController(self, self._device_catalogs)
        self._water_sensors = WaterSensorController(self, self._device_catalogs)

        self._image_sensors = ImageSensorController(self)
        self._image_sensor_images = ImageSensorImageController(self)

    async def initialize(self, event_monitoring: bool = False) -> None:
        """Initialize bridge."""

        await self.login()

        await self.fetch_full_state()

        if event_monitoring:
            await self._ws_controller.initialize()

        # Always subscribe in case of websocket connection later on.
        self._ws_controller.subscribe_connection(self._handle_connect_event)

        # TODO: REFRESH IMAGE SENSORS / PROFILE / ETC ON SCHEDULE
        # TODO: SKYBELL HD
        # TODO: Sensor Bypass
        # TODO: Partition WebSocket

    async def login(self) -> None:
        """Login to alarm.com."""

        self._ajax_key = None

        return await self._auth_controller.login()

    async def fetch_full_state(self) -> None:
        """Fetch full state from alarm.com."""

        # Get active system
        await self._available_device_catalogs.initialize()

        if not self._available_device_catalogs.active_system_id:
            raise AuthenticationFailed("No active system found.")

        await asyncio.gather(
            self._device_catalogs.initialize([self._available_device_catalogs.active_system_id]),
            self._partitions.initialize(),
            self._trouble_conditions.initialize()
            if self._auth_controller.has_trouble_conditions_service
            else asyncio.sleep(0),
        )

        await asyncio.gather(
            self._systems.initialize(),
            self._cameras.initialize(),
            self._garage_doors.initialize(),
            self._gates.initialize(),
            self._image_sensors.initialize(),
            self._image_sensor_images.initialize(),
            self._lights.initialize(),
            self._locks.initialize(),
            self._sensors.initialize(),
            self._thermostats.initialize(),
            self._water_sensors.initialize(),
        )

    def subscribe(
        self,
        callback: EventCallBackType,
    ) -> Callable:
        """
        Subscribe to status changes for all resources.

        Returns:
            function to unsubscribe.

        """
        unsubscribes = [
            self._systems.event_subscribe(callback),
            self._trouble_conditions.event_subscribe(callback),
            self._device_catalogs.event_subscribe(callback),
            self._cameras.event_subscribe(callback),
            self._garage_doors.event_subscribe(callback),
            self._lights.event_subscribe(callback),
            self._gates.event_subscribe(callback),
            self._locks.event_subscribe(callback),
            self._partitions.event_subscribe(callback),
            self._sensors.event_subscribe(callback),
            self._thermostats.event_subscribe(callback),
            self._water_sensors.event_subscribe(callback),
            self._image_sensors.event_subscribe(callback),
        ]

        def unsubscribe() -> None:
            for unsub in unsubscribes:
                unsub()

        return unsubscribe

    async def _handle_connect_event(self, state: WebSocketState) -> None:
        """Handle reconnect event from event controller."""

        if state == WebSocketState.RECONNECTED:
            await self.fetch_full_state()

    ###################
    # GET CONTROLLERS #
    ###################

    @property
    def lights(self) -> LightController:
        """Get the lights controller."""

        return self._lights

    @property
    def cameras(self) -> CameraController:
        """Get the cameras controller."""
        return self._cameras

    @property
    def garage_doors(self) -> GarageDoorController:
        """Get the garage doors controller."""
        return self._garage_doors

    @property
    def gates(self) -> GateController:
        """Get the gates controller."""
        return self._gates

    @property
    def image_sensors(self) -> ImageSensorController:
        """Get the image sensors controller."""
        return self._image_sensors

    @property
    def image_sensor_images(self) -> ImageSensorImageController:
        """Get the image sensor images controller."""
        return self._image_sensor_images

    @property
    def locks(self) -> LockController:
        """Get the locks controller."""
        return self._locks

    @property
    def partitions(self) -> PartitionController:
        """Get the partitions controller."""
        return self._partitions

    @property
    def sensors(self) -> SensorController:
        """Get the sensors controller."""
        return self._sensors

    @property
    def system(self) -> SystemController:
        """Get the system controller."""
        return self._systems

    @property
    def thermostats(self) -> ThermostatController:
        """Get the thermostats controller."""
        return self._thermostats

    @property
    def trouble_conditions(self) -> TroubleConditionController:
        """Get the trouble conditions controller."""
        return self._trouble_conditions

    @property
    def water_sensors(self) -> WaterSensorController:
        """Get the water sensors controller."""
        return self._water_sensors

    @property
    def auth_controller(self) -> AuthenticationController:
        """Get the authentication controller."""
        return self._auth_controller

    @property
    def ws_controller(self) -> WebSocketClient:
        """Get the websocket controller."""
        return self._ws_controller

    ##########################################
    # REQUEST MANAGEMENT / CONTEXT FUNCTIONS #
    ##########################################

    async def __aenter__(self) -> "AlarmBridge":  # noqa: UP037
        """Return Context manager."""

        await self.initialize(event_monitoring=True)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager."""

        await self.close()

    async def close(self) -> None:
        """Close connection and cleanup."""
        # await self.events.stop()
        if self._websession:
            await self._websession.close()
        log.info("Connection to alarm.com closed.")

    #
    # REQUEST FUNCTIONS
    #

    def build_request_headers(self, **kwargs: Any) -> Any:
        """Get session and build headers for request."""

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        kwargs["headers"].update(
            {
                "User-Agent": f"pyalarmdotcomajax/{__version__}",
                "Referrer": "https://www.alarm.com/web/system/home",
            }
        )

        kwargs["headers"].update({"Accept": "application/vnd.api+json", "charset": "utf-8"})

        if self._ajax_key:
            kwargs["headers"].update({"ajaxrequestuniquekey": self._ajax_key})

        return kwargs

    @contextlib.asynccontextmanager
    async def create_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        """
        Make a request to the Alarm.com API.

        Returns a generator with aiohttp ClientResponse.
        """

        if self._websession is None:
            # Required to allow for requests to be made while event listener is holding session open.
            connector = aiohttp.TCPConnector(
                limit_per_host=3,
            )
            self._websession = aiohttp.ClientSession(connector=connector)

        if "cookies" not in kwargs:
            kwargs["cookies"] = {}

        kwargs["cookies"].update({"twoFactorAuthenticationId": self._auth_controller.mfa_cookie})

        kwargs = self.build_request_headers(**kwargs)

        async with self._websession.request(method, url, **kwargs) as res:
            # Update anti-forgery cookie.

            # AFG cookie is not always used. This seems to depend on the specific Alarm.com vendor, so a missing AFG key should not cause a failure.
            # Ref: https://www.alarm.com/web/system/assets/addon-tree-output/@adc/ajax/services/adc-ajax.js
            # When used, AFG is not always present in the response. Prior value should carry over until a new value appears.

            if afg := res.cookies.get("afg"):
                self._ajax_key = afg.value

            yield res

    T = TypeVar("T", bound=JsonApiBaseElement)

    @contextlib.asynccontextmanager
    async def ws_connect(
        self,
        url: str,
        **kwargs: Any,
    ) -> AsyncIterator[aiohttp.ClientWebSocketResponse]:
        """
        Establish a WebSocket connection with Alarm.com.

        Returns a generator with aiohttp ClientWebSocketResponse.
        """
        if self._websession is None:
            raise NotInitialized("Cannot initiate WebSocket connection without an existing session.")

        kwargs = self.build_request_headers(**kwargs)

        async with self._websession.ws_connect(url, **kwargs) as res:
            yield res

    @overload
    async def request(
        self,
        method: str,
        url: str,
        success_response_class: type[JsonApiSuccessResponse] = JsonApiSuccessResponse,
        allow_login_repair: bool = True,
        **kwargs: Any,
    ) -> JsonApiSuccessResponse:
        ...

    @overload
    async def request(
        self,
        method: str,
        url: str,
        success_response_class: type[T],
        allow_login_repair: bool = True,
        **kwargs: Any,
    ) -> T:
        ...

    async def request(
        self,
        method: str,
        url: str,
        success_response_class: type[T] | type[JsonApiSuccessResponse] = JsonApiSuccessResponse,
        allow_login_repair: bool = True,
        **kwargs: Any,
    ) -> T | JsonApiSuccessResponse:
        """Make request to the api and return response data."""

        # Alarm.com's implementation violates the JSON:API spec by sometimes returning a modified error response body with a non-200 response code.
        # This response still contains an "errors" object and should validate as a JsonApiFailureResponse.

        try:
            async with self.create_request(method, url, **kwargs) as resp:
                # If DEBUG logging is enabled, log the request and response.
                if log.level < logging.DEBUG:
                    try:
                        resp_dump = json.dumps(await resp.json()) if resp.content_length else ""
                    except json.JSONDecodeError:
                        resp_dump = await resp.text() if resp.content_length else ""
                    log.debug(
                        f"\n==============================Server Response ({resp.status})==============================\n"
                        f"URL: {url}\n"
                        f"{resp_dump}"
                        f"\nURL: {url}"
                        "\n=================================================================================\n"
                    )

                # Load the response as JSON:API object.

                try:
                    jsonapi_response = success_response_class.from_json(await resp.text())
                except SuitableVariantNotFoundError as err:
                    # Triggered when the response is not valid JSON:API format.
                    raise UnexpectedResponse("Response was not valid JSON:API format.") from err
                except MissingField as err:
                    # Triggered when using a success_response_class that is not JsonApiSuccessResponse.
                    raise UnexpectedResponse("Response was missing a required field.") from err

                if isinstance(jsonapi_response, success_response_class):
                    return jsonapi_response

                if isinstance(jsonapi_response, JsonApiInfoResponse):
                    raise UnexpectedResponse("Unhandled JSON:API info response.")

                if isinstance(jsonapi_response, JsonApiFailureResponse):
                    # Retrieve errors from errors dict object.
                    error_codes = [int(error.code) for error in jsonapi_response.errors if error.code is not None]

                    # 406: Not Authorized For Ember, 423: Processing Error
                    if all(x in error_codes for x in [403, 426]):
                        log.info(
                            "Got a processing error. This may be caused by missing permissions, being on an Alarm.com plan without support for a particular device type, or having a device type disabled for this system."
                        )
                        raise NotAuthorized(
                            f"Method: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                        )

                    # 401: Logged Out, 403: Invalid Anti Forgery
                    if all(x in error_codes for x in [401, 403]):
                        raise AuthenticationFailed(
                            f"Method: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}",
                            can_autocorrect=True,
                        )

                    # 409: Two Factor Authentication Required
                    if 409 in error_codes:
                        raise AuthenticationFailed(
                            f"Two factor authentication required.\nMethod: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                        )

                    # 422: Wrong Two Factor Authentication Code
                    if 422 in error_codes:
                        raise AuthenticationFailed(
                            f"Method: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                        )

                    # 422: ValidationError, 500: ServerProcessingError, 503: ServiceUnavailable
                    raise UnexpectedResponse(
                        f"Method: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                    )

                resp.raise_for_status()

                # Bad things have happened if we reach this point.
                raise UnexpectedResponse

        except AuthenticationFailed as err:
            if err.can_autocorrect and allow_login_repair:
                log.info("Attempting to repair session.")

                try:
                    await self._auth_controller.login()
                    return await self.request(
                        method, url, success_response_class, allow_login_repair=False, **kwargs
                    )
                except Exception as err:
                    raise AuthenticationFailed from err

            raise

    @overload
    async def get(
        self,
        url: str,
        success_response_class: type[JsonApiSuccessResponse] = JsonApiSuccessResponse,
        **kwargs: Any,
    ) -> JsonApiSuccessResponse:
        ...

    @overload
    async def get(
        self,
        url: str,
        success_response_class: type[T],
        **kwargs: Any,
    ) -> T:
        ...

    async def get(
        self,
        url: str,
        success_response_class: type[T] | type[JsonApiSuccessResponse] = JsonApiSuccessResponse,
        **kwargs: Any,
    ) -> T | JsonApiSuccessResponse:
        """GET from server and return mashumaro deserialized JsonApiSuccessResponse."""

        retries = 0
        while True:
            try:
                return await self.request("get", url, success_response_class, **kwargs)

            except (TimeoutError, aiohttp.ClientResponseError) as e:
                if retries == REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from e
                retries += 1
                continue

    @overload
    async def post(
        self,
        url: str,
        success_response_class: type[JsonApiSuccessResponse] = JsonApiSuccessResponse,
        **kwargs: Any,
    ) -> JsonApiSuccessResponse:
        ...

    @overload
    async def post(
        self,
        url: str,
        success_response_class: type[T],
        **kwargs: Any,
    ) -> T:
        ...

    async def post(
        self,
        url: str,
        success_response_class: type[T] | type[JsonApiSuccessResponse] = JsonApiSuccessResponse,
        **kwargs: Any,
    ) -> T | JsonApiSuccessResponse:
        """POST to server and return mashumaro deserialized JsonApiSuccessResponse."""

        retries = 0
        while True:
            try:
                return await self.request("post", url, success_response_class, **kwargs)

            except (TimeoutError, aiohttp.ClientResponseError) as e:
                if retries == SUBMIT_RETRY_LIMIT:
                    raise ServiceUnavailable from e
                retries += 1
                continue


async def main() -> None:
    """Run application."""

    # Callable[[WebSocketNotificationType, WebSocketState | BaseWSMessage], Any]
    def event_printer(event_type: EventType, resource_id: str, resource: AdcResource | None) -> None:
        """Print event."""
        log.info(f"[NEW EVENT] {event_type} {resource_id} {resource}")

    # Get the credentials from environment variables
    username = str(os.environ.get("ADC_USERNAME"))
    password = str(os.environ.get("ADC_PASSWORD"))
    mfa_token = str(os.environ.get("ADC_COOKIE"))

    async with AlarmBridge(username, password, mfa_token) as bridge:
        bridge.subscribe(event_printer)

        await asyncio.sleep(3600)
    # Create an instance of AlarmConnector
    # bridge = AlarmBridge(username, password, mfa_token)

    # try:
    #     # Initialize the connector
    #     await bridge.initialize()

    #     # Perform other tasks here

    # finally:
    #     # Close the connector
    #     await bridge.close()


# Start the asyncio task
if __name__ == "__main__":
    asyncio.run(main())
