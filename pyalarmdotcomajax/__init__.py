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
import humps
from mashumaro.exceptions import MissingField, SuitableVariantNotFoundError

from pyalarmdotcomajax.const import REQUEST_RETRY_LIMIT, SUBMIT_RETRY_LIMIT, URL_BASE, ResponseTypes
from pyalarmdotcomajax.controllers import EventType
from pyalarmdotcomajax.controllers.auth import AuthenticationController
from pyalarmdotcomajax.controllers.base import AdcSuccessDocumentMulti, AdcSuccessDocumentSingle, EventCallBackType
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
from pyalarmdotcomajax.models.base import AdcResource, ResourceType
from pyalarmdotcomajax.models.jsonapi import (
    FailureDocument,
    JsonApiBaseElement,
    MetaDocument,
    SuccessDocument,
)
from pyalarmdotcomajax.websocket.client import WebSocketClient, WebSocketState

__version__ = "6.0.0-beta.1"


log = logging.getLogger(__name__)


class AlarmBridge:
    """Alarm.com bridge."""

    def __init__(self, username: str, password: str, mfa_token: str | None = None) -> None:
        """Initialize alarm bridge."""

        self._initialized = False

        # Session
        self._websession: aiohttp.ClientSession | None = None
        self.ajax_key: str | None = None

        # NEW CONTROLLERS MUST BE ADDED TO __str__()

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

    async def initialize(self) -> None:
        """Initialize bridge."""

        if self._initialized:
            return

        await self.login()

        await self.fetch_full_state()

        self._initialized = True

        # TODO: REFRESH IMAGE SENSORS / PROFILE / ETC ON SCHEDULE (DO IN INTEGRATION)
        # TODO: SKYBELL HD

    async def login(self) -> None:
        """Login to alarm.com."""

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

    async def start_event_monitoring(self) -> None:
        """Start real-time event monitoring."""

        await self._ws_controller.initialize()

        # Always subscribe in case of websocket connection later on.
        self._ws_controller.subscribe_connection(self._handle_connect_event)

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

    @property
    def device_catalogs(self) -> DeviceCatalogController:
        """Get the device catalogs controller."""
        return self._device_catalogs

    ##########################################
    # REQUEST MANAGEMENT / CONTEXT FUNCTIONS #
    ##########################################

    async def __aenter__(self) -> "AlarmBridge":  # noqa: UP037
        """Return Context manager."""

        await self.initialize()

        await self.start_event_monitoring()

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

    def build_request_headers(
        self,
        accept_types: ResponseTypes | None = ResponseTypes.JSONAPI,
        use_ajax_key: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Get session and build headers for request."""

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        kwargs["headers"].update(
            {
                "User-Agent": f"pyalarmdotcomajax/{__version__}",
                "Referrer": "https://www.alarm.com/web/system/home",
            }
        )

        if accept_types is not None:
            kwargs["headers"].update(accept_types.value)

        if use_ajax_key and self.ajax_key:
            kwargs["headers"].update({"Ajaxrequestuniquekey": self.ajax_key})

        return kwargs

    @contextlib.asynccontextmanager
    async def create_request(
        self,
        method: str,
        url: str,
        accept_types: ResponseTypes = ResponseTypes.JSONAPI,
        use_ajax_key: bool = True,
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

        kwargs = self.build_request_headers(accept_types, use_ajax_key, **kwargs)

        async with self._websession.request(method, url, **kwargs) as res:
            # Update anti-forgery cookie.

            # AFG cookie is not always used. This seems to depend on the specific Alarm.com vendor, so a missing AFG key should not cause a failure.
            # Ref: https://www.alarm.com/web/system/assets/addon-tree-output/@adc/ajax/services/adc-ajax.js
            # When used, AFG is not always present in the response. Prior value should carry over until a new value appears.

            if afg := res.cookies.get("afg"):
                self.ajax_key = afg.value

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

        kwargs = self.build_request_headers(accept_types=None, use_ajax_key=False, **kwargs)

        async with self._websession.ws_connect(url, **kwargs) as res:
            yield res

    @overload
    async def request(
        self,
        method: str,
        url: str,
        accept_types: ResponseTypes,
        success_response_class: type[T],
        **kwargs: Any,
    ) -> T: ...

    @overload
    async def request(
        self,
        method: str,
        url: str,
        accept_types: ResponseTypes,
        success_response_class: type[SuccessDocument] = SuccessDocument,
        **kwargs: Any,
    ) -> SuccessDocument: ...

    async def request(
        self,
        method: str,
        url: str,
        accept_types: ResponseTypes = ResponseTypes.JSONAPI,
        success_response_class: type[T] | type[SuccessDocument] = SuccessDocument,
        allow_login_repair: bool = True,
        **kwargs: Any,
    ) -> T | SuccessDocument:
        """Make request to the api and return response data."""

        # Alarm.com's implementation violates the JSON:API spec by sometimes returning a modified error response body with a non-200 response code.
        # This response still contains an "errors" object and should validate as a FailureDocument.

        log.debug(
            f"Requesting {method.upper()} {url} with {kwargs.get('data') or kwargs.get('json')} expecting {accept_types} as {success_response_class.__name__}"
        )

        try:
            async with self.create_request(method, url, accept_types, use_ajax_key=True, **kwargs) as resp:
                # If DEBUG logging is enabled, log the request and response.
                if log.level < logging.DEBUG:
                    try:
                        resp_dump = json.dumps(await resp.json()) if resp.content_length else ""
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        resp_dump = await resp.text() if resp.content_length else ""

                    log.debug(
                        f"\n==============================Server Request / Response ({resp.status})==============================\n"
                        f"URL: {url}\n"
                        f"REQUEST HEADERS:\n{json.dumps(dict(resp.request_info.headers)) }\n"
                        f"RESPONSE BODY:\n{resp_dump}\n"
                        f"URL: {url}\n"
                        "=================================================================================\n"
                    )

                # Load the response as JSON:API object.

                try:
                    jsonapi_response = success_response_class.from_json(await resp.text())
                except SuitableVariantNotFoundError as err:
                    # Triggered when the response is not valid JSON:API format.
                    raise UnexpectedResponse("Response was not valid JSON:API format.") from err
                except MissingField as err:
                    # Triggered when using a success_response_class that is not SuccessDocument.
                    raise UnexpectedResponse("Response was missing a required field.") from err
                except json.JSONDecodeError as err:
                    # Triggered when the response is not valid JSON.
                    raise UnexpectedResponse("Response was not valid JSON.") from err

                if isinstance(jsonapi_response, success_response_class):
                    return jsonapi_response

                if isinstance(jsonapi_response, MetaDocument):
                    raise UnexpectedResponse("Unhandled JSON:API info response.")

                resp.raise_for_status()

                if isinstance(jsonapi_response, FailureDocument):
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

                # resp.raise_for_status()

                # Bad things have happened if we reach this point.
                raise UnexpectedResponse

        except AuthenticationFailed as err:
            if err.can_autocorrect and allow_login_repair:
                log.info("Attempting to repair session.")

                try:
                    log.info("[AlarmBridge -> request] Attempting to repair session.")
                    await self._auth_controller.login()
                    return await self.request(
                        method,
                        url,
                        success_response_class=success_response_class,
                        allow_login_repair=False,
                        **kwargs,
                    )
                except Exception as err:
                    raise AuthenticationFailed from err

            raise

    def _generate_request_url(self, path: ResourceType | str, id: str | set[str] | None) -> str:
        """Generate request URL."""

        # Format path for appropriate resource type & pluralize.
        if isinstance(path, ResourceType):
            path = humps.camelize(path.value) + "s"
        else:
            path.rstrip("/")

        if isinstance(id, set) and len(id) == 1:
            id = id.pop()

        # Format path for single/multi/all.
        if isinstance(id, str):
            # Set path for single resource.
            path += f"/{id}"

        elif isinstance(id, set):
            # Explode IDs if id is a list.
            path += "?" + "&".join([f"ids[]={n}" for n in id])

        return f"{URL_BASE}web/api/{path}"

    @overload
    async def get(
        self,
        path: ResourceType | str,
        id: str,
        **kwargs: Any,
    ) -> AdcSuccessDocumentSingle: ...

    @overload
    async def get(
        self,
        path: ResourceType | str,
        id: set[str] | None,
        **kwargs: Any,
    ) -> AdcSuccessDocumentMulti: ...

    async def get(
        self,
        path: ResourceType | str,
        id: str | set[str] | None,
        **kwargs: Any,
    ) -> AdcSuccessDocumentSingle | AdcSuccessDocumentMulti:
        """
            Get resources from the server.

        Args:
            id:         the id(s) of the resource(s) to get. if str, get one resource. if set, get specified. if None, get all.
                        requests for single devices must use the single device format (/devices/locks/12345-098), not the multi-device format (/devices/locks?id[]=12345-098).
            path:       the path of the resource to get. if ResourceType, build path based on resource type. if str, use as is in place of ResourceType-generated path.
            kwargs:     additional arguments to pass to the request.

        Returns:
            AdcSuccessDocumentMulti: the response from the server.

        """

        path = self._generate_request_url(path, id)

        retries = 0
        while True:
            try:
                return await self.request(
                    method="get",
                    url=path,
                    accept_types=ResponseTypes.JSONAPI,
                    success_response_class=AdcSuccessDocumentSingle
                    if isinstance(id, str)
                    else AdcSuccessDocumentMulti,
                    **kwargs,
                )

            except (TimeoutError, aiohttp.ClientResponseError) as e:
                if retries == REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from e
                retries += 1
                continue

    async def post(
        self,
        path: ResourceType | str,
        id: str | set[str] | None,
        action: str | None,
        **kwargs: Any,
    ) -> AdcSuccessDocumentSingle:
        """POST to server and return mashumaro deserialized SuccessDocument."""

        path = self._generate_request_url(path, id) + (f"/{action}" if action else "/")

        retries = 0
        while True:
            try:
                return await self.request(
                    method="post",
                    url=path,
                    accept_types=ResponseTypes.JSONAPI,
                    success_response_class=AdcSuccessDocumentSingle,
                    **kwargs,
                )

            except (TimeoutError, aiohttp.ClientResponseError) as e:
                if retries == SUBMIT_RETRY_LIMIT:
                    raise ServiceUnavailable from e
                retries += 1
                continue

    ############################
    ## RESOURCE STRING OUTPUT ##
    ############################

    @property
    def resources_pretty_str(self) -> str:
        """Return pretty representation of resources in AlarmBridge."""

        # Print all controllers
        return (
            self._auth_controller.resources_pretty_str
            + self._available_device_catalogs.resources_pretty_str
            + self._systems.resources_pretty_str
            + self._trouble_conditions.resources_pretty_str
            + self._device_catalogs.resources_pretty_str
            + self._cameras.resources_pretty_str
            + self._garage_doors.resources_pretty_str
            + self._lights.resources_pretty_str
            + self._gates.resources_pretty_str
            + self._locks.resources_pretty_str
            + self._partitions.resources_pretty_str
            + self._sensors.resources_pretty_str
            + self._thermostats.resources_pretty_str
            + self._water_sensors.resources_pretty_str
            + self._image_sensors.resources_pretty_str
        )

    @property
    def resources_raw_str(self) -> str:
        """Return raw JSON for all bridge resources."""

        return (
            self._auth_controller.resources_raw_str
            + self._available_device_catalogs.resources_raw_str
            + self._systems.resources_raw_str
            + self._trouble_conditions.resources_raw_str
            + self._device_catalogs.resources_raw_str
            + self._cameras.resources_raw_str
            + self._garage_doors.resources_raw_str
            + self._lights.resources_raw_str
            + self._gates.resources_raw_str
            + self._locks.resources_raw_str
            + self._partitions.resources_raw_str
            + self._sensors.resources_raw_str
            + self._thermostats.resources_raw_str
            + self._water_sensors.resources_raw_str
            + self._image_sensors.resources_raw_str
        )


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

    # # Create an instance of AlarmConnector
    # bridge = AlarmBridge(username, password, mfa_token)

    # try:
    #     # Initialize the connector
    #     await bridge.initialize()

    #     # Perform other tasks here
    #     print(bridge.resources_raw_str)

    # finally:
    #     # Close the connector
    #     await bridge.close()


# Start the asyncio task
if __name__ == "__main__":
    asyncio.run(main())
