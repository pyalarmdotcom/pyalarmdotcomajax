"""Alarmdotcom API Controller."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import Callable, Coroutine
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any, TypedDict

import aiohttp
from bs4 import BeautifulSoup

from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.const import OtpType
from pyalarmdotcomajax.devices import (
    BaseDevice,
    DeviceTypeSpecificData,
    TroubleCondition,
)
from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.devices.registry import (
    AllDevices_t,
    AttributeRegistry,
    DeviceRegistry,
    DeviceType,
)
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
    OtpRequired,
    SessionTimeout,
    TryAgain,
    UnexpectedResponse,
    UnsupportedDeviceType,
)
from pyalarmdotcomajax.extensions import (
    CameraSkybellControllerExtension,
    ConfigurationOption,
    ControllerExtensions_t,
    ExtendedProperties,
)
from pyalarmdotcomajax.websockets.client import WebSocketClient, WebSocketState

__version__ = "0.5.4"

log = logging.getLogger(__name__)


class ExtensionResults(TypedDict):
    """Results of multi-device extension calls."""

    settings: dict[str, ConfigurationOption]
    controller: ControllerExtensions_t


class AlarmController:
    """Base class for communicating with Alarm.com via API."""

    HOME_URL = "https://www.alarm.com/web/system/home"
    UA = f"pyalarmdotcomajax/{__version__}"

    AJAX_HEADERS_TEMPLATE = {
        "Accept": "application/vnd.api+json",
        "User-Agent": UA,
        "Referrer": HOME_URL,
        "ajaxrequestuniquekey": None,
    }

    ALL_DEVICES_URL_TEMPLATE = (  # Substitute with base url and system ID.
        "{}web/api/settings/manageDevices/deviceCatalogs/{}"
    )
    ALL_SYSTEMS_URL_TEMPLATE = "{}web/api/systems/availableSystemItems?searchString="
    ALL_RECENT_IMAGES_TEMPLATE = "{}web/api/imageSensor/imageSensorImages/getRecentImages"

    # LOGIN & SESSION: BEGIN
    LOGIN_TWO_FACTOR_COOKIE_NAME = "twoFactorAuthenticationId"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"  # noqa: S105
    LOGIN_REMEMBERME_FIELD = "ctl00$ContentPlaceHolder1$loginform$chkRememberMe"

    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
    LOGIN_2FA_POST_URL_TEMPLATE = (
        "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/verifyTwoFactorCode"
    )
    LOGIN_2FA_DETAIL_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}"
    LOGIN_2FA_TRUST_URL_TEMPLATE = (
        "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/trustTwoFactorDevice"
    )
    LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaSms"
    LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE = "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaEmail"

    VIEWSTATE_FIELD = "__VIEWSTATE"
    VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
    EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
    PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

    KEEP_ALIVE_DEFAULT_URL = "/web/KeepAlive.aspx"
    KEEP_ALIVE_URL_PARAM_TEMPLATE = "?timestamp={}"
    KEEP_ALIVE_RENEW_SESSION_URL_TEMPLATE = "{}web/api/identities/{}/reloadContext"
    KEEP_ALIVE_SIGNAL_INTERVAL_S = 60
    SESSION_REFRESH_DEFAULT_INTERVAL_MS = 780000  # 13 minutes. Sessions expire at 15.

    # LOGIN & SESSION: END

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        twofactorcookie: str | None = None,
    ):
        """Manage access to Alarm.com API and builds devices."""

        #
        # SET
        #
        self._username: str = username
        self._password: str = password
        self._websession: aiohttp.ClientSession = websession
        self._two_factor_cookie: dict = {"twoFactorAuthenticationId": twofactorcookie} if twofactorcookie else {}

        #
        # INITIALIZE
        #

        self._provider_name: str | None = None
        self._user_id: str | None = None
        self._user_email: str | None = None
        self._active_system_id: str | None = None
        self._ajax_headers: dict = self.AJAX_HEADERS_TEMPLATE

        self._partition_map: dict = (
            {}
        )  # Individual devices don't list their associated partitions. This map is used to retrieve partition id when each device is created.

        self._installed_device_types: set[DeviceType] = (
            set()
        )  # List of device types that are present in a user's environment. We'll use this to cut down on the number of API calls made.

        self._trouble_conditions: dict = {}

        self.devices: DeviceRegistry = DeviceRegistry()

        #
        # WEBSOCKET ATTRIBUTES
        #

        self._ws_state_callback: Callable[[WebSocketState], None] | None = None
        self._websocket: WebSocketClient | None = None

        #
        # SESSION ATTRIBUTES
        #

        self._session_refresh_interval_ms: int = self.SESSION_REFRESH_DEFAULT_INTERVAL_MS
        self._keep_alive_url: str = self.KEEP_ALIVE_DEFAULT_URL
        self._last_session_refresh: datetime = datetime.now()
        self._session_timer: SessionTimer | None = None

        #
        # CLI ATTRIBUTES
        #
        self.raw_catalog: dict = {}
        self.raw_system: dict = {}
        self.raw_image_sensors: dict = {}
        self.raw_recent_images: dict = {}

    #
    #
    ##############
    # PROPERTIES #
    ##############
    #
    #

    @property
    def provider_name(self) -> str | None:
        """Return provider name."""
        return self._provider_name

    @property
    def user_id(self) -> str | None:
        """Return user ID."""
        return self._user_id

    @property
    def user_email(self) -> str | None:
        """Return user email address."""
        return self._user_email

    @property
    def two_factor_cookie(self) -> str | None:
        """Return two factor cookie."""
        return (
            cookie
            if isinstance(self._two_factor_cookie, dict)
            and (cookie := self._two_factor_cookie.get(self.LOGIN_TWO_FACTOR_COOKIE_NAME))
            else None
        )

    #
    #
    ####################
    # PUBLIC FUNCTIONS #
    ####################
    #
    #

    async def async_update(self) -> None:
        """Pull latest device data from Alarm.com.

        Raises:
            OtpRequired: Username and password are correct. User now needs to begin two-factor authentication workflow.
            ConfigureTwoFactorAuthentication: Alarm.com requires that the user set up two-factor authentication for their account.
            UnexpectedResponse: Server returned status code >=400 or response object was not as expected.
            aiohttp.ClientError: Connection error.
            asyncio.TimeoutError: Connection error due to timeout.
            NotAuthorized: User doesn't have permission to perform the action requested.
            AuthenticationFailed: User could not be logged in, likely due to invalid credentials.
            UnsupportedDeviceType: Device type is not supported by this library.
        """

        log.debug("Calling update on Alarm.com")

        has_image_sensors: bool = False

        if not self._active_system_id:
            self._active_system_id = await self._async_get_active_system()
            has_image_sensors = await self._async_has_image_sensors(self._active_system_id)

        await self._async_get_trouble_conditions()

        #
        # GET CORE DEVICE ATTRIBUTES
        #

        device_instances: dict[str, AllDevices_t] = {}
        raw_devices: list[dict] = await self._async_get_system(self._active_system_id)
        raw_devices.extend(await self._async_get_system_devices(self._active_system_id))

        #
        # QUERY MULTI-DEVICE EXTENSIONS
        #

        extension_results = await self._async_update__query_multi_device_extensions(raw_devices)

        #
        # QUERY IMAGE SENSORS
        #
        # Detailed image sensors data is not included in the main device catalog. It must be queried separately.
        #
        # TODO: Convert image sensors images to device extension. Merge entity_specific_data and settings; eliminate "additional endpoints" concept. Maybe push processing/placement into specific device class.

        device_type_specific_data = {}

        if has_image_sensors:
            # Get detailed image sensor data and add to raw device list.
            image_sensors = await self._async_get_devices_by_device_type(DeviceType.IMAGE_SENSOR)
            raw_devices.extend(image_sensors)

            # Get recent images
            device_type_specific_data = await self._async_get_recent_images()

        #
        # BUILD PARTITIONS
        #

        # Ensure that partition map is built before devices are built.

        for partition_raw in [
            partition_raw
            for partition_raw in raw_devices
            if partition_raw["type"] == AttributeRegistry.get_relationship_id_from_devicetype(DeviceType.PARTITION)
        ]:
            partition_instance: AllDevices_t = await self._async_update__build_device(
                partition_raw, device_type_specific_data, extension_results
            )

            for child, _ in partition_instance.children:
                self._partition_map[child] = partition_instance.id_

            device_instances.update({partition_instance.id_: partition_instance})

            raw_devices.remove(partition_raw)

            #
            # BUILD ALL DEVICES IN PARTITION
            #
            # This ensures that partition map is built before devices are built.

            for device_raw in raw_devices:
                try:
                    device_instance: AllDevices_t = await self._async_update__build_device(
                        device_raw, device_type_specific_data, extension_results
                    )

                    device_instances.update({device_instance.id_: device_instance})

                except UnsupportedDeviceType:
                    continue

        self.devices.update(device_instances, purge=True)

    async def async_send_command(
        self,
        device_type: DeviceType,
        event: BaseDevice.Command,
        device_id: str,  # ID corresponds to device_type
        msg_body: dict = {},  # Body of request. No abstractions here.
        retry_on_failure: bool = True,  # Set to prevent infinite loops when function calls itself
    ) -> dict:
        """Send commands to Alarm.com."""
        log.info("Sending %s to Alarm.com.", event)

        msg_body["statePollOnly"] = False

        try:
            url = (
                f"{AttributeRegistry.get_endpoints(device_type)['primary'].format(c.URL_BASE, device_id)}/{event.value}"
            )
        except KeyError as err:
            raise UnsupportedDeviceType(device_type, device_id) from err

        log.debug("Url %s", url)

        try:
            async with self._websession.post(
                url=url, json=msg_body, headers=self._ajax_headers, raise_for_status=True
            ) as resp:
                log.debug("Response from Alarm.com %s", resp.status)

                json_rsp = await resp.json()

                # Special handling of 422 status.
                # 422 sometimes occurs when forceBypass is True but there's nothing to bypass.
                if (
                    str(resp.status) == "422"
                    and isinstance(event, Partition.Command)
                    and (msg_body.get("forceBypass") is True)
                ):
                    log.debug(
                        "Error executing %s, trying again without force bypass...",
                        event.value,
                    )

                    # Not changing retry_on_failure. Changing forcebypass means that we won't re-enter this block.

                    msg_body["forceBypass"] = False

                    return await self.async_send_command(
                        device_type=device_type,
                        event=event,
                        device_id=device_id,
                        msg_body=msg_body,
                    )

                # Run standard server response checks.
                await self._async_handle_server_errors(json_rsp, "send_command", retry_on_failure)

                # If above pass and we have a 200, we're good.
                if str(resp.status) == "200":
                    return dict(json_rsp)

        except aiohttp.ClientResponseError as err:
            log.exception("Failed to send command.")
            raise UnexpectedResponse from err

        except TryAgain:
            return await self.async_send_command(
                device_type=device_type,
                event=event,
                device_id=device_id,
                msg_body=msg_body,
                retry_on_failure=False,
            )
        else:
            log.exception(
                f"{event.value} failed with HTTP code {resp.status}. URL: {url}\nJSON: {msg_body}\nHeaders:"
                f" {self._ajax_headers}"
            )
            raise UnexpectedResponse

    async def start_session_nudger(self) -> None:
        """Start task to nudge user sessions to keep from timing out."""

        self._session_timer = SessionTimer(self.keep_alive, self.KEEP_ALIVE_SIGNAL_INTERVAL_S)
        await self._session_timer.start()

    async def stop_session_nudger(self) -> None:
        """Stop session nudger."""

        if self._session_timer:
            await self._session_timer.stop()

    #
    # WEBSOCKET FUNCTIONS
    #

    def start_websocket(self, ws_state_callback: Callable[[WebSocketState], None] | None = None) -> None:
        """Construct and return a websocket client."""

        self._ws_state_callback = ws_state_callback

        self._websocket = WebSocketClient(
            self._websession, self._ajax_headers, self.devices, self._ws_state_callback
        )
        self._websocket.start()

    def stop_websocket(self) -> None:
        """Close websession and websocket to UniFi."""
        log.info("Closing WebSocket connection.")
        if self._websocket:
            self._websocket.stop()

    #
    # AUTHENTICATION FUNCTIONS
    #

    async def async_login(
        self,
    ) -> None:
        """Log in to Alarm.com.

        Raises:
            OtpRequired: Username and password are correct. User now needs to begin two-factor authentication workflow.
            ConfigureTwoFactorAuthentication: Alarm.com requires that the user set up two-factor authentication for their account.
            UnexpectedResponse: Server returned status code >=400 or response object was not as expected.
            aiohttp.ClientError: Connection error.
            asyncio.TimeoutError: Connection error due to timeout.
            NotAuthorized: User doesn't have permission to perform the action requested.
            AuthenticationFailed: User could not be logged in, likely due to invalid credentials.
        """
        log.debug("Attempting to log in to Alarm.com")

        #
        # Step 1: Get login page and cookies
        #

        try:
            # load login page once and grab VIEWSTATE/cookies
            async with self._websession.get(url=self.LOGIN_URL, cookies=None) as resp:
                text = await resp.text()
                log.debug("Response status from Alarm.com: %s", resp.status)
                tree = BeautifulSoup(text, "html.parser")
                login_info = {
                    self.VIEWSTATE_FIELD: tree.select(f"#{self.VIEWSTATE_FIELD}")[0].attrs.get("value"),
                    self.VIEWSTATEGENERATOR_FIELD: tree.select(f"#{self.VIEWSTATEGENERATOR_FIELD}")[0].attrs.get(
                        "value"
                    ),
                    self.EVENTVALIDATION_FIELD: tree.select(f"#{self.EVENTVALIDATION_FIELD}")[0].attrs.get(
                        "value"
                    ),
                    self.PREVIOUSPAGE_FIELD: tree.select(f"#{self.PREVIOUSPAGE_FIELD}")[0].attrs.get("value"),
                }

        except aiohttp.ClientResponseError as err:
            log.exception("Failed to load login page.")
            raise UnexpectedResponse from err
        except (AttributeError, IndexError) as err:
            log.exception("Unable to extract login info from Alarm.com")
            raise UnexpectedResponse from err

        #
        # Step 2: Log in and save anti-forgery key
        #

        try:
            # login and grab ajax key
            async with self._websession.post(
                url=self.LOGIN_POST_URL,
                data={
                    self.LOGIN_USERNAME_FIELD: self._username,
                    self.LOGIN_PASSWORD_FIELD: self._password,
                    self.VIEWSTATE_FIELD: login_info[self.VIEWSTATE_FIELD],
                    self.VIEWSTATEGENERATOR_FIELD: login_info[self.VIEWSTATEGENERATOR_FIELD],
                    self.EVENTVALIDATION_FIELD: login_info[self.EVENTVALIDATION_FIELD],
                    self.PREVIOUSPAGE_FIELD: login_info[self.PREVIOUSPAGE_FIELD],
                    "__EVENTTARGET": None,
                    "__EVENTARGUMENT": None,
                    "__VIEWSTATEENCRYPTED": None,
                    "IsFromNewSite": "1",
                },
                cookies=self._two_factor_cookie,
                raise_for_status=True,
            ) as resp:
                if re.search("m=login_fail", str(resp.url)) is not None:
                    log.exception("Login failed.")
                    log.exception("\nResponse URL:\n%s\n", str(resp.url))
                    log.exception("\nRequest Headers:\n%s\n", str(resp.request_info.headers))
                    raise AuthenticationFailed("Invalid username and password.")

                # Update anti-forgery cookie.
                # AFG cookie is not always present in the response. This seems to depend on the specific Alarm.com vendor, so a missing AFG key should not cause a failure.
                # Ref: https://www.alarm.com/web/system/assets/addon-tree-output/@adc/ajax/services/adc-ajax.js

                with contextlib.suppress(KeyError):
                    self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception("Failed to get AJAX key from Alarm.com.")
            raise UnexpectedResponse from err

        self._last_session_refresh = datetime.now()

        log.debug("Logged in to Alarm.com.")

        #
        # Step 3: Get user's profile.
        #

        async with self._websession.get(
            url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await resp.json()

            try:
                self._user_id = json_rsp["data"][0]["id"]
                self._provider_name = json_rsp["data"][0]["attributes"]["logoName"]
                self._provider_name = json_rsp["data"][0]["attributes"]["logoName"]

                for inclusion in json_rsp["included"]:
                    if inclusion["id"] == self._user_id and inclusion["type"] == "profile/profile":
                        self._user_email = inclusion["attributes"]["loginEmailAddress"]

                if not self._user_email:
                    raise UnexpectedResponse("Failed to get user's email address.")
            except KeyError as err:
                log.exception(f"{__name__} _async_get_identity_info: Failed to get user's identity info.")
                log.debug(
                    f"{__name__} _async_get_identity_info: Server Response:\n{json.dumps(json_rsp, indent=4)}"
                )
                raise AuthenticationFailed from err

            try:
                self._session_refresh_interval_ms = json_rsp["data"][0]["attributes"][
                    "applicationSessionProperties"
                ]["inactivityWarningTimeoutMs"]

                if not self._session_refresh_interval_ms:
                    raise KeyError

            except KeyError:
                self._session_refresh_interval_ms = self.SESSION_REFRESH_DEFAULT_INTERVAL_MS

            try:
                self._keep_alive_url = json_rsp["data"][0]["attributes"]["applicationSessionProperties"][
                    "keepAliveUrl"
                ]

                if not self._keep_alive_url:
                    raise KeyError

            except KeyError:
                self._keep_alive_url = self.KEEP_ALIVE_DEFAULT_URL

            log.debug("*** START IDENTITY INFO ***")
            log.debug(f"Provider: {self._provider_name}")
            log.debug(f"User: {self._user_id} {self._user_email}")
            log.debug(f"Keep Alive Interval: {self._session_refresh_interval_ms}")
            log.debug(f"Keep Alive URL: {self._keep_alive_url}")
            log.debug("*** END IDENTITY INFO ***")

        #
        # Step 4: Determine whether OTP is required
        #

        try:
            async with self._websession.get(
                url=self.LOGIN_2FA_DETAIL_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

            await self._async_handle_server_errors(json_rsp, "2FA requirements", False)

        except aiohttp.ClientResponseError as err:
            log.exception("Failed to get 2FA requirements.")
            raise UnexpectedResponse from err

        if not (attribs := json_rsp.get("data", {}).get("attributes")):
            raise UnexpectedResponse("Could not find expected data in two-factor authentication details.")

        if attribs.get("showSuggestedSetup") is True:
            raise ConfigureTwoFactorAuthentication

        enabled_otp_types_bitmask = attribs.get("enabledTwoFactorTypes")
        enabled_2fa_methods = [
            otp_type for otp_type in OtpType if bool(enabled_otp_types_bitmask & otp_type.value)
        ]

        if (
            (OtpType.disabled in enabled_2fa_methods)
            or (attribs.get("isCurrentDeviceTrusted") is True)
            or not enabled_otp_types_bitmask
            or not enabled_2fa_methods
        ):
            # 2FA is disabled, we can skip 2FA altogether.
            return

        log.info(f"Requires two-factor authentication. Enabled methods are {enabled_2fa_methods}")

        raise OtpRequired(enabled_2fa_methods)

    async def async_request_otp(self, method: OtpType | None) -> None:
        """Request SMS/email OTP code from Alarm.com."""

        log.debug("Requesting OTP code...")

        if method not in (OtpType.email, OtpType.sms):
            return

        request_url = (
            self.LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE
            if method == OtpType.email
            else self.LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE
        )
        try:
            async with self._websession.post(
                url=request_url.format(c.URL_BASE, self._user_id),
                headers=self._ajax_headers,
                raise_for_status=True,
            ):
                pass

        except aiohttp.ClientResponseError as err:
            log.exception("Failed to get available systems.")
            raise UnexpectedResponse from err

    async def async_submit_otp(
        self, code: str, method: OtpType, device_name: str | None = None, remember_me: bool = False
    ) -> None:
        """Submit two factor authentication code.

        Register device and return 2FA code if device_name is not None.
        """

        # Submit code
        try:
            log.debug("Submitting OTP code...")

            async with self._websession.post(
                url=self.LOGIN_2FA_POST_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
                headers=self._ajax_headers,
                json={"code": code, "typeOf2FA": method.value},
                raise_for_status=True,
            ) as resp:
                json_rsp = await resp.json()

        except aiohttp.ClientResponseError as err:
            if err.status == 422:
                raise AuthenticationFailed("Wrong code.") from err
            raise UnexpectedResponse from err

        log.debug("Submitted OTP code.")

        if not device_name and not remember_me:
            log.debug('Skipping "Remember Me".')
            return

        # Submit device name for "remember me" function.
        if suggested_device_name := json_rsp.get("value", {}).get("deviceName"):
            try:
                log.debug("Registering device...")

                async with self._websession.post(
                    url=self.LOGIN_2FA_TRUST_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
                    headers=self._ajax_headers,
                    json={"deviceName": device_name if device_name else suggested_device_name},
                    raise_for_status=True,
                ) as resp:
                    json_rsp = await resp.json()
            except aiohttp.ClientResponseError as err:
                log.exception("Failed to send command.")
                raise UnexpectedResponse from err

            log.debug("Registered device.")

        # Save 2FA cookie value.
        for cookie in self._websession.cookie_jar:
            if cookie.key == self.LOGIN_TWO_FACTOR_COOKIE_NAME:
                log.debug("Found two-factor authentication cookie: %s", cookie.value)
                self._two_factor_cookie = {"twoFactorAuthenticationId": cookie.value} if cookie.value else {}
                return

        raise UnexpectedResponse("Failed to find two-factor authentication cookie.")

    async def is_logged_in(self, throw: bool = False) -> bool:
        """Check if we are still logged in."""

        url = f"{c.URL_BASE[:-1]}{self._keep_alive_url}{self.KEEP_ALIVE_URL_PARAM_TEMPLATE.format(int(round(datetime.now().timestamp())))}"

        text_rsp: str

        try:
            async with self._websession.get(
                url=url,
                headers=self._ajax_headers,
                raise_for_status=True,
            ) as resp:
                text_rsp = await resp.text()

        except aiohttp.ClientResponseError as err:
            if err.status == 403:
                log.debug("Session expired.")

                if throw:
                    raise SessionTimeout

                return False

            raise UnexpectedResponse(f"Failed to send keep alive signal. Response: {text_rsp}") from err

        return True

    async def keep_alive(self) -> None:
        """Keep session alive. Handle if not (optionally).

        Should be called once per minute to keep session alive.
        """

        reload_context_now = (
            self._last_session_refresh + timedelta(milliseconds=self._session_refresh_interval_ms)
        ) < datetime.now()

        seconds_remaining = (
            self._last_session_refresh
            + (timedelta(milliseconds=self._session_refresh_interval_ms))
            - datetime.now()
        ).total_seconds()

        debug_message = "Sending keep alive signal. Time until session context refresh: {}".format(
            "imminent" if reload_context_now else f"~ {round((seconds_remaining % 3600) // 60)} minutes."
        )
        log.debug(debug_message)

        try:
            if await self.is_logged_in(throw=True) and reload_context_now:
                await self._reload_session_context()
        except SessionTimeout:
            log.info("User session expired. Logging back in.")
            await self.async_login()

    #
    #
    #####################
    # PRIVATE FUNCTIONS #
    #####################
    #

    async def _reload_session_context(self) -> None:
        """Check if we are still logged in."""

        log.debug("Reloading session context.")

        async with self._websession.post(
            url=self.KEEP_ALIVE_RENEW_SESSION_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
            headers=self._ajax_headers,
            data=json.dumps({"included": [], "meta": {"transformer_version": "1.1"}}),
        ) as resp:
            json_rsp = await resp.json()

            if resp.status >= 400:
                raise UnexpectedResponse(f"Failed to reload session context. Response: {json_rsp}")

            self._last_session_refresh = datetime.now()

    async def _async_update__build_device(
        self,
        raw_device: dict,
        device_type_specific_data: dict[str, DeviceTypeSpecificData],
        extension_results: dict[str, ExtensionResults],
    ) -> AllDevices_t:
        """Build device instance."""

        #
        # DETERMINE DEVICE'S PYALARMDOTCOMAJAX PYTHON CLASS & DEVICETYPE
        #
        device_type: DeviceType = AttributeRegistry.get_devicetype_from_relationship_id(raw_device["type"])
        device_class: type[AllDevices_t] = AttributeRegistry.get_class(device_type)

        #
        # SKIP UNSUPPORTED DEVICE TYPES
        #
        # There is a hack here for cameras. We don't really support cameras (no images / streaming), we only support settings for the Skybell HD.
        if not AttributeRegistry.is_supported(device_type) or (
            (device_type == DeviceType.CAMERA)
            and (raw_device.get("attributes", {}).get("deviceModel") != "SKYBELLHD")
        ):
            raise UnsupportedDeviceType(device_type, raw_device.get("id"))

        children: list[tuple[str, DeviceType]] = []

        # Get child elements for partitions and systems if function called using a device_type.
        if device_type in [DeviceType.PARTITION, DeviceType.SYSTEM]:
            for family_name, family_data in raw_device["relationships"].items():
                if DeviceType.has_value(family_name):
                    for sub_device in family_data["data"]:
                        children.append((sub_device["id"], DeviceType(family_name)))

        #
        # BUILD DEVICE INSTANCE
        #

        entity_id = raw_device["id"]

        device_extension_results: ExtensionResults | dict = extension_results.get(entity_id, {})

        return device_class(
            id_=entity_id,
            raw_device_data=raw_device,
            children=children,
            device_type_specific_data=device_type_specific_data.get(entity_id),
            send_action_callback=self.async_send_command,
            config_change_callback=(
                extension_controller.submit_change
                if (extension_controller := device_extension_results.get("controller"))
                else None
            ),
            trouble_conditions=self._trouble_conditions.get(entity_id),
            partition_id=self._partition_map.get(entity_id),
            settings=device_extension_results.get("settings"),
        )

    async def _async_update__query_multi_device_extensions(
        self, raw_devices: list[dict]
    ) -> dict[str, ExtensionResults]:
        """Query device extensions that request data for multiple devices at once.

        Args:
            raw_devices: A list of devices to query.

        Returns:
            A dict containing a dictionary with the device id, device extensions, and a
            ControllerExtensions_t object.

        """

        required_extensions: list[type[ControllerExtensions_t]] = []
        name_id_map: dict[str, str] = {}

        #
        # Check whether any devices have extensions.
        #

        for raw_device in raw_devices:
            device_type: DeviceType = AttributeRegistry.get_devicetype_from_relationship_id(raw_device["type"])

            #
            # Camera Skybell HD Extension
            # Skybell HD extension pulls data for all cameras at once.
            #
            if (
                device_type == DeviceType.CAMERA
                and raw_device.get("attributes", {}).get("deviceModel") == "SKYBELLHD"
            ):
                required_extensions.append(CameraSkybellControllerExtension)
                # Stop searching at the first hit since once we have a Skybell, we know that we need to query the extension.
                break

        if not required_extensions:
            return {}

        #
        # Build map of device names -> device ids.
        #

        for raw_device in raw_devices:
            if name := raw_device.get("attributes", {}).get("description"):
                name_id_map[name] = raw_device["id"]

        #
        # Retrieve data for extensions
        #

        results: dict[str, ExtensionResults] = {}

        for extension_t in required_extensions:
            extension_controller = extension_t(
                websession=self._websession,
                headers=self._ajax_headers,
            )

            try:
                # Fetch from Alarm.com
                extended_properties_by_device: list[ExtendedProperties] = await extension_controller.fetch()
            except UnexpectedResponse:
                continue

            # Match extended properties to devices by name, then add to storage.

            for device_properties in extended_properties_by_device:
                if (device_name := device_properties.device_name) in name_id_map:
                    device_id = name_id_map[device_name]
                    results[device_id] = {
                        "settings": device_properties.settings,
                        "controller": extension_controller,
                    }

        return results

    async def _async_get_active_system(self, retry_on_failure: bool = True) -> str:
        """Get active system for user account."""

        try:
            log.info("Getting active system.")

            async with self._websession.get(
                url=self.ALL_SYSTEMS_URL_TEMPLATE.format(c.URL_BASE),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                await self._async_handle_server_errors(json_rsp, "active system", retry_on_failure)

                return str(
                    [system["id"] for system in json_rsp.get("data", []) if system["attributes"]["isSelected"]][0]
                )

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception("Failed to get active system.")
            raise UnexpectedResponse from err
        except TryAgain:
            if retry_on_failure:
                return await self._async_get_active_system(retry_on_failure=False)

            raise

    async def _async_get_recent_images(self) -> dict[str, DeviceTypeSpecificData]:
        """Get recent images."""

        try:
            log.info("Getting recent images.")

            async with self._websession.get(
                url=self.ALL_RECENT_IMAGES_TEMPLATE.format(c.URL_BASE),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

            # Used by adc CLI.
            self.raw_recent_images = json_rsp

            if resp.status >= 400 or not isinstance(json_rsp, dict) or not len(json_rsp.get("data", [])):
                return {}

            device_type_specific_data: dict[str, DeviceTypeSpecificData] = {}

            for image in json_rsp["data"]:
                device_type_specific_data.setdefault(
                    str(image["relationships"]["imageSensor"]["data"]["id"]), {}
                ).setdefault("raw_recent_images", []).append(image)

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception("Failed to get recent images.")
            raise UnexpectedResponse from err

        else:
            return device_type_specific_data

    async def _async_has_image_sensors(self, system_id: str, retry_on_failure: bool = True) -> bool:
        """Check whether image sensors are present in system.

        Check is required because image sensors are not shown in the device catalog endpoint.
        """

        # TODO: Needs changes to support multi-system environments

        try:
            log.info(f"Checking system {system_id} for image sensors.")

            # Find image sensors.

            async with self._websession.get(
                url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(c.URL_BASE, system_id),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                await self._async_handle_server_errors(json_rsp, "image sensors", retry_on_failure)

                return len(json_rsp["data"].get("relationships", {}).get("imageSensors", {}).get("data", [])) > 0

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception("Failed to get image sensors.")
            raise UnexpectedResponse from err
        except TryAgain:
            if retry_on_failure:
                return await self._async_has_image_sensors(system_id, retry_on_failure=False)

            raise

    async def _async_get_system(self, system_id: str, retry_on_failure: bool = True) -> list[dict]:
        """Get all devices present in system."""

        try:
            log.info(f"Getting system data for {system_id}.")

            async with self._websession.get(
                url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(c.URL_BASE, system_id),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                # Used by adc CLI.
                self.raw_system = json_rsp

                await self._async_handle_server_errors(json_rsp, "system", retry_on_failure)

                return [json_rsp["data"]]

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception("Failed to get system metadata.")
            raise UnexpectedResponse from err
        except TryAgain:
            return await self._async_get_system(system_id=system_id, retry_on_failure=False)

    async def _async_get_system_devices(self, system_id: str, retry_on_failure: bool = True) -> list[dict]:
        """Get all devices present in system."""

        try:
            log.info(f"Getting all devices in {system_id}.")

            async with self._websession.get(
                url=self.ALL_DEVICES_URL_TEMPLATE.format(c.URL_BASE, system_id),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                # Used by adc CLI.
                self.raw_catalog = json_rsp

                await self._async_handle_server_errors(json_rsp, "system devices", retry_on_failure)

                return [
                    device
                    for device in json_rsp["included"]
                    if device.get("type") in AttributeRegistry.all_relationship_ids
                ]

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception("Failed to get system devices.")
            raise UnexpectedResponse from err
        except TryAgain:
            return await self._async_get_system_devices(system_id=system_id, retry_on_failure=False)

    async def _async_get_devices_by_device_type(
        self, device_type: DeviceType, retry_on_failure: bool = True
    ) -> list[dict]:
        """Get all devices of the specified type."""

        try:
            log.info(f"Getting all {device_type.value}.")

            async with self._websession.get(
                url=AttributeRegistry.get_endpoints(device_type)["primary"].format(c.URL_BASE, ""),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                # Used by adc CLI.
                if device_type == DeviceType.IMAGE_SENSOR:
                    self.raw_image_sensors = json_rsp

                await self._async_handle_server_errors(json_rsp, f"get all {device_type.value}", retry_on_failure)

                return list(json_rsp["data"])

        except (aiohttp.ClientResponseError, KeyError) as err:
            log.exception(f"Failed to get devices of type {device_type}.")
            raise UnexpectedResponse from err
        except TryAgain:
            return await self._async_get_devices_by_device_type(device_type=device_type, retry_on_failure=False)

    async def _async_get_trouble_conditions(self, retry_on_failure: bool = True) -> None:
        """Get trouble conditions for all devices."""

        # TODO: Trouble condition dict should be flagged, not None, when library encounters an error retrieving trouble conditions.

        try:
            async with self._websession.get(
                url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                log.debug("Trouble condition response:\n%s", json_rsp)

                await self._async_handle_server_errors(json_rsp, "active system", retry_on_failure)

                trouble_all_devices: dict = {}
                for condition in json_rsp.get("data", []):
                    device_id = condition.get("attributes", {}).get("emberDeviceId")
                    new_trouble: TroubleCondition = {
                        "message_id": condition.get("id"),
                        "title": condition.get("attributes", {}).get("description"),
                        "body": condition.get("attributes", {}).get("extraData", {}).get("description"),
                        "device_id": device_id,
                    }

                    trouble_single_device: list = trouble_all_devices.get(device_id, [])
                    trouble_single_device.append(new_trouble)
                    trouble_all_devices[device_id] = trouble_single_device

                self._trouble_conditions = trouble_all_devices

        except aiohttp.ContentTypeError as err:
            self._trouble_conditions = {}
            log.exception(
                "Server returned wrong content type. Response: %s\n\nResponse Text:\n\n%s\n\n",
                resp,
                resp.text(),
            )
            raise UnexpectedResponse from err

        except aiohttp.ClientResponseError as err:
            log.exception("Failed to get trouble conditions.")
            raise UnexpectedResponse from err

        except KeyError as err:
            self._trouble_conditions = {}
            log.exception("Failed processing trouble conditions.")
            raise UnexpectedResponse from err

        except TryAgain:
            return await self._async_get_trouble_conditions(retry_on_failure=False)

    async def _async_handle_server_errors(
        self, json_rsp: dict, request_name: str, retry_on_failure: bool = False
    ) -> None:
        """Handle errors returned by the server."""

        log.debug(
            "\n==============================\nServer"
            f" Response:\n{json.dumps(json_rsp)}\n=============================="
        )

        if not len(rsp_errors := json_rsp.get("errors", [])):
            return

        log.debug(
            error_msg := f"{__name__}: Request error. Status: {rsp_errors[0].get('status')}. Response: {json_rsp}"
        )

        match rsp_errors[0].get("status"):
            case "423":  # Processing Error
                log.exception(
                    f"Got a processing error when trying to request {request_name}. This may be caused by missing"
                    " permissions, being on an Alarm.com plan without support for a particular device type, or"
                    " having a device type disabled for this system."
                )
                log.debug(error_msg := f"{request_name} failed.\nResponse:\n{json_rsp}.")
                raise NotAuthorized

            case "403":  # Invalid Anti-Forgery Token
                # 403 means that either the user doesn't have access to this class of device or that the user has logged out.
                # Unsupported device types should be stripped out in async_update(), so assume logged out.
                # If logged out, try logging in again, then give up by pretending that we couldn't find any devices of this type.

                if not retry_on_failure:
                    log.error(
                        "Error fetching data from Alarm.com. Got 403 status when"
                        f" fetching {request_name}. Logging in"
                        " again didn't help. Giving up on device type."
                    )
                    raise UnexpectedResponse(error_msg)

                if not self.is_logged_in():
                    log.info(
                        "Error fetching data from Alarm.com. Got 403 status"
                        f" when requesting {request_name}. Trying to"
                        " refresh auth tokens by logging in again."
                    )

                    await self.async_login()

                    raise TryAgain

            case "409":
                log.exception(
                    error_msg := f"Failed to request {request_name}. Two factor authentication cookie is incorrect."
                )
                log.debug(error_msg := f"{request_name} failed.\nResponse:\n{json_rsp}.")
                raise AuthenticationFailed(error_msg)

            case _:
                log.exception(f"Unknown error while requesting {request_name}.")
                log.debug(error_msg := f"{request_name} failed.\nResponse:\n{json_rsp}.")
                raise UnexpectedResponse(error_msg)


class SessionTimer:
    """Run keep_alive function periodically to keep session alive."""

    # https://stackoverflow.com/a/37514633

    def __init__(self, func: Callable[[], Coroutine[Any, Any, Any]], time: float) -> None:
        """Initialize SessionTimer. Takes time in seconds."""
        self.func = func
        self.time: float = time
        self.is_started: bool = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start SessionTimer."""
        if not self.is_started:
            self.is_started = True
            # Start task to call func periodically:
            self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        """Stop SessionTimer."""
        if self.is_started:
            self.is_started = False
            # Stop task and await it stopped:
            if self._task:
                self._task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._task

    async def _run(self) -> None:
        """Run task and sleep."""
        while True:
            await asyncio.sleep(self.time)
            await self.func()
