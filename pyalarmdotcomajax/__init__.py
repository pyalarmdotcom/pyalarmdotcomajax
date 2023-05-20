"""Alarmdotcom API Controller."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import TypedDict

import aiohttp
from bs4 import BeautifulSoup

from pyalarmdotcomajax import const as c
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
from pyalarmdotcomajax.errors import (
    AuthenticationFailed,
    DataFetchFailed,
    TryAgain,
    TwoFactor_ConfigurationRequired,
    TwoFactor_OtpRequired,
    UnexpectedDataStructure,
    UnsupportedDevice,
)
from pyalarmdotcomajax.extensions import (
    CameraSkybellControllerExtension,
    ConfigurationOption,
    ControllerExtensions_t,
    ExtendedProperties,
)
from pyalarmdotcomajax.websockets.client import WebSocketClient, WebSocketState

# TODO: Use error handler and exception handlers in _async_get_system_devices on other request functions.
# TODO: Fix get raw server response function.

__version__ = "0.5.0-beta.4"

log = logging.getLogger(__name__)


class ExtensionResults(TypedDict):
    """Results of multi-device extension calls."""

    settings: dict[str, ConfigurationOption]
    controller: ControllerExtensions_t


class OtpType(Enum):
    """Alarm.com two factor authentication type."""

    # https://www.alarm.com/web/system/assets/customer-ember/enums/TwoFactorAuthenticationType.js
    # Keep these lowercase. Strings.json in Home Assistant requires lowercase values.

    disabled = 0
    app = 1
    sms = 2
    email = 4


class AlarmController:
    """Base class for communicating with Alarm.com via API."""

    AJAX_HEADERS_TEMPLATE = {
        "Accept": "application/vnd.api+json",
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

    KEEP_ALIVE_CHECK_URL_TEMPLATE = "{}web/KeepAlive.aspx?timestamp={}"
    KEEP_ALIVE_CHECK_RESPONSE = '{"status":"Keep Alive"}'
    KEEP_ALIVE_URL = "{}web/api/identities/{}/reloadContext"
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

        self._ws_state_callback: Callable[[WebSocketState], None] | None = None
        self._websocket: WebSocketClient | None = None

        self._partition_map: dict = (
            {}
        )  # Individual devices don't list their associated partitions. This map is used to retrieve partition id when each device is created.

        self._installed_device_types: set[DeviceType] = (
            set()
        )  # List of device types that are present in a user's environment. We'll use this to cut down on the number of API calls made.

        self._trouble_conditions: dict = {}

        self.devices: DeviceRegistry = DeviceRegistry()

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

    async def async_update(self) -> None:  # noqa: C901
        """Fetch latest device data."""

        log.debug("Calling update on Alarm.com")

        has_image_sensors: bool = False

        if not self._active_system_id:
            self._active_system_id = await self._async_get_active_system()
            has_image_sensors = await self._async_has_image_sensors(self._active_system_id)

        with contextlib.suppress(DataFetchFailed, UnexpectedDataStructure):
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

        for device in [
            device
            for device in raw_devices
            if device["type"] == AttributeRegistry.get_relationship_id_from_devicetype(DeviceType.PARTITION)
        ]:
            partition_instance: AllDevices_t = await self._async_update__build_device(
                device, device_type_specific_data, extension_results
            )

            for child, _ in partition_instance.children:
                self._partition_map[child] = partition_instance.id_

            device_instances.update({partition_instance.id_: partition_instance})

            raw_devices.remove(device)

            #
            # BUILD ALL DEVICES IN PARTITION
            #
            # This ensures that partition map is built before devices are built.

            for device in raw_devices:
                try:
                    device_instance: AllDevices_t = await self._async_update__build_device(
                        device, device_type_specific_data, extension_results
                    )

                    device_instances.update({device_instance.id_: device_instance})

                except UnsupportedDevice:
                    continue

        self.devices.update(device_instances, purge=True)

    async def async_send_command(
        self,
        device_type: DeviceType,
        event: BaseDevice.Command,
        device_id: str | None = None,  # ID corresponds to device_type
        msg_body: dict = {},  # Body of request. No abstractions here.
        retry_on_failure: bool = True,  # Set to prevent infinite loops when function calls itself
    ) -> bool:
        """Send commands to Alarm.com."""
        log.info("Sending %s to Alarm.com.", event)

        msg_body["statePollOnly"] = False

        try:
            url = (
                f"{AttributeRegistry.get_endpoints(device_type)['primary'].format(c.URL_BASE, device_id)}/{event.value}"
            )
        except KeyError as err:
            raise UnsupportedDevice from err

        log.debug("Url %s", url)

        async with self._websession.post(url=url, json=msg_body, headers=self._ajax_headers) as resp:
            log.debug("Response from Alarm.com %s", resp.status)

            match str(resp.status):
                case "200":
                    # Update entities after calling state change.
                    # TODO: Confirm that we can remove this call because of webhook support.
                    # await self.async_update()
                    return True

                case "423":
                    # User has read-only permission to the entity.
                    err_msg = (
                        f"{__name__}: User {self.user_email} has read-only access to"
                        f" {device_type.name.lower()} {device_id}."
                    )
                    raise PermissionError(err_msg)

                case "422":
                    if isinstance(event, Partition.Command) and (msg_body.get("forceBypass") is True):
                        # 422 sometimes occurs when forceBypass is True but there's nothing to bypass.
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

                case "403":
                    # May have been logged out, try again
                    log.warning(
                        "Error executing %s, NOT logging in and trying again...",
                        event.value,
                    )

                    return False
                    # if retry_on_failure:
                    #     await self.async_login()
                    #     return await self.async_send_command(
                    #         device_type,
                    #         event,
                    #         device_id,
                    #         msg_body,
                    #         False,
                    #     )

        log.error(
            f"{event.value} failed with HTTP code {resp.status}. URL: {url}\nJSON: {msg_body}\nHeaders:"
            f" {self._ajax_headers}"
        )
        raise ConnectionError

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
        """Login to Alarm.com."""
        log.debug("Attempting to log in to Alarm.com")

        # TODO: Prevent login from making a ton of saved devices in ADC.

        try:
            await self._async_login_and_get_key()
            await self._async_get_identity_info()

            # Check whether two factor authentication is required.
            if not self._two_factor_cookie:
                async with self._websession.get(
                    url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(c.URL_BASE, ""),
                    headers=self._ajax_headers,
                ) as resp:
                    json_rsp = await resp.json()

                    log.debug(f"Response from Alarm.com login: {resp.status} {resp.json()}")

                for error in (errors := json_rsp.get("errors", {})):
                    if error.get("status") == "409" and error.get("detail") == "TwoFactorAuthenticationRequired":
                        log.debug("Two factor authentication code or cookie required.")
                        raise TwoFactor_OtpRequired

        except (DataFetchFailed, UnexpectedDataStructure) as err:
            raise ConnectionError from err
        except (AuthenticationFailed, PermissionError) as err:
            raise AuthenticationFailed from err
        except TwoFactor_ConfigurationRequired as err:
            raise err

        log.info("Logged in successfully.")
        return None

    async def async_get_enabled_2fa_methods(self) -> list[OtpType]:
        """Get list of two factor authentication methods enabled on account."""

        async with self._websession.get(
            url=self.LOGIN_2FA_DETAIL_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await resp.json()
            enabled_otp_types_bitmask = json_rsp.get("data", {}).get("attributes", {}).get("enabledTwoFactorTypes")
            enabled_2fa_methods = [
                otp_type for otp_type in OtpType if bool(enabled_otp_types_bitmask & otp_type.value)
            ]
            log.info(f"Requires two-factor authentication. Enabled methods are {enabled_2fa_methods}")
            return enabled_2fa_methods

    async def async_request_otp(self, method: OtpType | None) -> None:
        """Request SMS/email OTP code from Alarm.com."""

        if method not in (OtpType.email, OtpType.sms):
            return None

        try:
            log.debug("Requesting OTP code...")

            request_url = (
                self.LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE
                if method == OtpType.email
                else self.LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE
            )

            async with self._websession.post(
                url=request_url.format(c.URL_BASE, self._user_id),
                headers=self._ajax_headers,
            ) as resp:
                if resp.status != 200:
                    raise DataFetchFailed("Failed to request 2FA code.")

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not load 2FA submission page from Alarm.com")
            raise DataFetchFailed from err

        return None

    async def async_submit_otp(self, code: str, method: OtpType, device_name: str | None = None) -> str | None:
        """Submit two factor authentication code.

        Register device and return 2FA code if device_name is not None.
        """

        # Submit code
        try:
            log.debug("Submitting OTP code...")

            if not method:
                raise AuthenticationFailed("Missing OTP type.")

            async with self._websession.post(
                url=self.LOGIN_2FA_POST_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
                headers=self._ajax_headers,
                json={"code": code, "typeOf2FA": method.value},
            ) as resp:
                json_rsp = await resp.json()

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not load 2FA submission page from Alarm.com")
            raise DataFetchFailed from err

        if resp.status == 422:
            raise AuthenticationFailed("Wrong code.")
        if resp.status > 400:
            log.error(
                "Failed 2FA submission with status %s: %s",
                resp.status,
                await resp.text(),
            )
            raise DataFetchFailed("Unknown error.")

        log.debug("Submitted OTP code.")

        if not device_name:
            log.debug('Skipping "Remember Me".')
            return None

        # Submit device name for "remember me" function.
        if json_rsp.get("value", {}).get("deviceName"):
            try:
                log.debug("Registering device...")

                async with self._websession.post(
                    url=self.LOGIN_2FA_TRUST_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
                    headers=self._ajax_headers,
                    json={"deviceName": device_name},
                ) as resp:
                    json_rsp = await resp.json()
            except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                log.error("Can not load device trust page from Alarm.com")
                raise DataFetchFailed from err

            log.debug("Registered device.")

        # Save 2FA cookie value.
        for cookie in self._websession.cookie_jar:
            if cookie.key == self.LOGIN_TWO_FACTOR_COOKIE_NAME:
                log.debug("Found two-factor authentication cookie: %s", cookie.value)
                self._two_factor_cookie = {"twoFactorAuthenticationId": cookie.value} if cookie.value else {}
                return str(cookie.value)

        log.error("Failed to find two-factor authentication cookie.")
        return None

    #
    #
    #####################
    # PRIVATE FUNCTIONS #
    #####################
    #
    # Communicate directly with the ADC API

    async def _async_keep_alive_login_check(self) -> bool:
        """Check if we are logged in."""

        async with self._websession.get(
            url=self.KEEP_ALIVE_CHECK_URL_TEMPLATE.format(c.URL_BASE, int(round(datetime.now().timestamp()))),
            headers=self._ajax_headers,
        ) as resp:
            text_rsp = await resp.text()

        return bool(text_rsp == self.KEEP_ALIVE_CHECK_RESPONSE)

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
            raise UnsupportedDevice(f"Unsupported device type: {device_type}")

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

        device_extension_results: ExtensionResults | dict = extension_results.get(
            entity_id := raw_device["id"], {}
        )

        device_instance = device_class(
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

        return device_instance

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
            if device_type == DeviceType.CAMERA:
                if raw_device.get("attributes", {}).get("deviceModel") == "SKYBELLHD":
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
            except UnexpectedDataStructure:
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

    async def _async_get_active_system(self) -> str:
        """Get active system for user account."""

        try:
            log.info("Getting active system.")

            async with self._websession.get(
                url=self.ALL_SYSTEMS_URL_TEMPLATE.format(c.URL_BASE),
                headers=self._ajax_headers,
                raise_for_status=True,
            ) as resp:
                json_rsp = await resp.json()

                return str(
                    [system["id"] for system in json_rsp.get("data", []) if system["attributes"]["isSelected"]][0]
                )

        except (asyncio.TimeoutError, aiohttp.ClientError, aiohttp.ClientResponseError, KeyError) as err:
            log.error("Failed to get available systems.")
            raise DataFetchFailed from err

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

            return device_type_specific_data

        except (asyncio.TimeoutError, aiohttp.ClientError, KeyError) as err:
            log.error("Failed to get available systems.")
            raise DataFetchFailed from err

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
                raise_for_status=True,
            ) as resp:
                json_rsp = await resp.json()

                await self._async_handle_server_errors(json_rsp, "image sensors", retry_on_failure)

                return len(json_rsp["data"].get("relationships", {}).get("imageSensors", {}).get("data", [])) > 0

        except (asyncio.TimeoutError, aiohttp.ClientError, aiohttp.ClientResponseError, KeyError) as err:
            log.error("Failed to get image sensors.")
            raise DataFetchFailed from err

    async def _async_get_system(self, system_id: str, retry_on_failure: bool = True) -> list[dict]:
        """Get all devices present in system."""

        try:
            log.info(f"Getting system data for {system_id}.")

            async with self._websession.get(
                url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(c.URL_BASE, system_id),
                headers=self._ajax_headers,
                raise_for_status=True,
            ) as resp:
                json_rsp = await resp.json()

                # Used by adc CLI.
                self.raw_system = json_rsp

                await self._async_handle_server_errors(json_rsp, "system", retry_on_failure)

                return [json_rsp["data"]]

        except (asyncio.TimeoutError, aiohttp.ClientError, aiohttp.ClientResponseError, KeyError) as err:
            log.error("Failed to get system devices.")
            raise DataFetchFailed from err
        except TryAgain:
            return await self._async_get_system(system_id=system_id, retry_on_failure=False)

    async def _async_get_system_devices(self, system_id: str, retry_on_failure: bool = True) -> list[dict]:
        """Get all devices present in system."""

        try:
            log.info(f"Getting all devices in {system_id}.")

            async with self._websession.get(
                url=self.ALL_DEVICES_URL_TEMPLATE.format(c.URL_BASE, system_id),
                headers=self._ajax_headers,
                raise_for_status=True,
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

        except (asyncio.TimeoutError, aiohttp.ClientError, aiohttp.ClientResponseError, KeyError) as err:
            log.error("Failed to get system devices.")
            raise DataFetchFailed from err
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
                raise_for_status=True,
            ) as resp:
                json_rsp = await resp.json()

                # Used by adc CLI.
                if device_type == DeviceType.IMAGE_SENSOR:
                    self.raw_image_sensors = json_rsp

                await self._async_handle_server_errors(json_rsp, f"get all {device_type.value}", retry_on_failure)

                return list(json_rsp["data"])

        except (asyncio.TimeoutError, aiohttp.ClientError, aiohttp.ClientResponseError, KeyError) as err:
            log.error(f"Failed to get {device_type.value}.")
            raise DataFetchFailed from err
        except TryAgain:
            return await self._async_get_devices_by_device_type(device_type=device_type, retry_on_failure=False)

    async def _async_get_identity_info(self) -> None:
        """Get user id, email address, provider name, etc."""
        try:
            async with self._websession.get(
                url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
                headers=self._ajax_headers,
                cookies=self._two_factor_cookie,
            ) as resp:
                json_rsp = await resp.json()

                self._user_id = json_rsp["data"][0]["id"]
                self._provider_name = json_rsp["data"][0]["attributes"]["logoName"]

                for inclusion in json_rsp["included"]:
                    if inclusion["id"] == self._user_id and inclusion["type"] == "profile/profile":
                        self._user_email = inclusion["attributes"]["loginEmailAddress"]

            if self._user_email is None:
                raise AuthenticationFailed("Could not find user email address.")

            log.debug("Got Provider: %s, User ID: %s", self._provider_name, self._user_id)

        except KeyError as err:
            log.error(f"{__name__} _async_get_identity_info: Failed to get user's identity info.")
            log.debug(f"{__name__} _async_get_identity_info: Server Response:\n{json.dumps(json_rsp, indent=4)}")
            raise AuthenticationFailed from err

    async def _async_get_trouble_conditions(self) -> None:
        """Get trouble conditions for all devices."""

        # TODO: Trouble condition dict should be flagged, not None, when library encounters an error retrieving trouble conditions.

        try:
            async with self._websession.get(
                url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await resp.json()

                log.debug("Trouble condition response:\n%s", json_rsp)

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
            log.error(
                "Server returned wrong content type. Response: %s\n\nResponse Text:\n\n%s\n\n",
                resp,
                resp.text(),
            )
            raise DataFetchFailed from err

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            self._trouble_conditions = {}
            log.error("Connection error while fetching trouble conditions.")
            raise DataFetchFailed from err

        except KeyError as err:
            self._trouble_conditions = {}
            log.error("Failed processing trouble conditions.")
            raise UnexpectedDataStructure from err

    async def _async_handle_server_errors(
        self, json_rsp: dict, request_name: str, retry_on_failure: bool = False
    ) -> None:
        """Handle errors returned by the server."""

        log.debug(
            f"\n==============================\nServer Response:\n{json_rsp}\n=============================="
        )

        if not len(rsp_errors := json_rsp.get("errors", [])):
            return

        log.debug(
            error_msg := f"{__name__}: Request error. Status: {rsp_errors[0].get('status')}. Response: {json_rsp}"
        )

        match rsp_errors[0].get("status"):
            case "423":  # Processing Error
                log.error(
                    f"Got a processing error when trying to request {request_name}. This may be caused by missing"
                    " permissions, being on an Alarm.com plan without support for a particular device type, or"
                    " having a device type disabled for this system."
                )
                log.debug(error_msg := f"{request_name} failed.\nResponse:\n{json_rsp}.")
                raise PermissionError

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
                    raise DataFetchFailed(error_msg)

                if not self._async_keep_alive_login_check():
                    log.debug(
                        "Error fetching data from Alarm.com. Got 403 status"
                        f" when requesting {request_name}. Trying to"
                        " refresh auth tokens by logging in again."
                    )

                    await self.async_login()

                    raise TryAgain

            case "409":
                log.error(
                    error_msg := f"Failed to request {request_name}. Two factor authentication cookie is incorrect."
                )
                log.debug(error_msg := f"{request_name} failed.\nResponse:\n{json_rsp}.")
                raise AuthenticationFailed(error_msg)

            case _:
                log.error(f"Unknown error while requesting {request_name}.")
                log.debug(error_msg := f"{request_name} failed.\nResponse:\n{json_rsp}.")
                raise DataFetchFailed(error_msg)

    async def _async_login_and_get_key(self) -> None:
        """Load hidden fields from login page."""
        try:
            # load login page once and grab VIEWSTATE/cookies
            async with self._websession.get(url=self.LOGIN_URL, cookies=self._two_factor_cookie) as resp:
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

        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
            asyncio.exceptions.CancelledError,
        ) as err:
            log.error("Can not load login page from Alarm.com")

            raise err
        except (AttributeError, IndexError) as err:
            log.error("Unable to extract login info from Alarm.com")
            raise UnexpectedDataStructure from err
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
                    "IsFromNewSite": "1",
                },
                cookies=self._two_factor_cookie,
            ) as resp:
                if re.search("m=login_fail", str(resp.url)) is not None:
                    log.error("Login failed.")
                    log.error("\nResponse URL:\n%s\n", str(resp.url))
                    log.error("\nRequest Headers:\n%s\n", str(resp.request_info.headers))
                    raise AuthenticationFailed("Invalid username and password.")

                # If Alarm.com is warning us that we'll have to set up two factor authentication soon, alert caller.
                if re.search("concurrent-two-factor-authentication", str(resp.url)) is not None:
                    raise TwoFactor_ConfigurationRequired("Encountered 2FA nag screen.")

                # Update anti-forgery cookie
                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not login to Alarm.com")
            raise DataFetchFailed from err
        except KeyError as err:
            log.error("Unable to extract ajax key from Alarm.com. Response:\n%s", resp)
            raise DataFetchFailed from err

        log.debug("Logged in to Alarm.com.")
