"""Alarmdotcom API Controller."""
from __future__ import annotations

import asyncio
from enum import Enum
import json
import logging
import re

import aiohttp
from aiohttp.client_exceptions import ContentTypeError
from bs4 import BeautifulSoup
from pyalarmdotcomajax.helpers import slug_to_title

from . import const as c
from .devices import BaseDevice
from .devices import Camera
from .devices import DEVICE_URLS
from .devices import DeviceType
from .devices import ElementSpecificData
from .devices import GarageDoor
from .devices import ImageSensor
from .devices import Light
from .devices import Lock
from .devices import Partition
from .devices import Sensor
from .devices import System
from .devices import TroubleCondition
from .errors import AuthenticationFailed
from .errors import BadAccount
from .errors import DataFetchFailed
from .errors import NagScreen
from .errors import UnexpectedDataStructure
from .errors import UnsupportedDevice
from .extensions import CameraSkybellControllerExtension
from .extensions import ConfigurationOption
from .extensions import ExtendedProperties

__version__ = "0.3.0"


log = logging.getLogger(__name__)

DEVICE_CLASSES: dict = {
    DeviceType.CAMERA: Camera,
    DeviceType.GARAGE_DOOR: GarageDoor,
    DeviceType.IMAGE_SENSOR: ImageSensor,
    DeviceType.LIGHT: Light,
    DeviceType.LOCK: Lock,
    DeviceType.PARTITION: Partition,
    DeviceType.SENSOR: Sensor,
    DeviceType.SYSTEM: System,
}


class AuthResult(Enum):
    """Standard for reporting results of login attempt."""

    SUCCESS = "success"
    OTP_REQUIRED = "otp_required"
    ENABLE_TWO_FACTOR = "enable_two_factor"


class OtpType(Enum):
    """Alarm.com two factor authentication type."""

    # https://www.alarm.com/web/system/assets/customer-ember/enums/TwoFactorAuthenticationType.js

    DISABLED = 0
    APP = 1
    SMS = 2
    EMAIL = 4


class AlarmController:
    """Base class for communicating with Alarm.com via API."""

    AJAX_HEADERS_TEMPLATE = {
        "Accept": "application/vnd.api+json",
        "ajaxrequestuniquekey": None,
    }

    # LOGIN & SESSION: BEGIN
    LOGIN_TWO_FACTOR_COOKIE_NAME = "twoFactorAuthenticationId"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"  # nosec

    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
    LOGIN_2FA_POST_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/verifyTwoFactorCode"
    LOGIN_2FA_DETAIL_URL_TEMPLATE = (
        "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}"
    )
    LOGIN_2FA_TRUST_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/trustTwoFactorDevice"
    LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCode"
    LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaEmail"

    IDENTITIES_2FA_NAG_URL_TEMPLATE = "{}system-install/api/identity"

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
        self._two_factor_cookie: dict = (
            {"twoFactorAuthenticationId": twofactorcookie} if twofactorcookie else {}
        )

        #
        # INITIALIZE
        #
        self._factor_type_id: int | None = None
        self._two_factor_method: OtpType | None = None
        self._provider_name: str | None = None
        self._user_id: str | None = None
        self._user_email: str | None = None
        self._ajax_headers: dict = self.AJAX_HEADERS_TEMPLATE

        # Individual devices don't list their associated partitions. This map is used to retrieve partition id when each device is created.
        self._partition_map: dict = {}

        self._trouble_conditions: dict = {}

        self.systems: list[System] = []
        self.partitions: list[Partition] = []
        self.sensors: list[Sensor] = []
        self.locks: list[Lock] = []
        self.garage_doors: list[GarageDoor] = []
        self.image_sensors: list[ImageSensor] = []
        self.lights: list[Light] = []
        self.cameras: list[Camera] = []

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
            and (
                cookie := self._two_factor_cookie.get(self.LOGIN_TWO_FACTOR_COOKIE_NAME)
            )
            else None
        )

    #
    #
    ####################
    # PUBLIC FUNCTIONS #
    ####################
    #
    #

    async def async_login(self, request_otp: bool = True) -> AuthResult:
        """Login to Alarm.com."""
        log.debug("Attempting to log in to Alarm.com")

        try:
            await self._async_login_and_get_key()
            await self._async_get_identity_info()

            if not self._two_factor_cookie and await self._async_requires_2fa():
                log.debug("Two factor authentication code or cookie required.")

                if request_otp and self._two_factor_method in [
                    OtpType.SMS,
                    OtpType.EMAIL,
                ]:
                    await self.async_request_otp()

                return AuthResult.OTP_REQUIRED

        except (DataFetchFailed, UnexpectedDataStructure) as err:
            raise ConnectionError from err
        except (AuthenticationFailed, PermissionError) as err:
            raise AuthenticationFailed from err
        except NagScreen:
            return AuthResult.ENABLE_TWO_FACTOR

        return AuthResult.SUCCESS

    async def async_request_otp(self) -> str | None:
        """Request SMS/email OTP code from Alarm.com."""

        try:

            log.debug("Requesting OTP code...")

            request_url = (
                self.LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE
                if self._two_factor_method == OtpType.EMAIL
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

    async def async_submit_otp(
        self, code: str, device_name: str | None = None
    ) -> str | None:
        """
        Submit two factor authentication code.

        Register device and return 2FA code if device_name is not None.
        """

        # Submit code
        try:

            log.debug("Submitting OTP code...")

            if not self._two_factor_method:
                raise AuthenticationFailed("Missing OTP type.")

            async with self._websession.post(
                url=self.LOGIN_2FA_POST_URL_TEMPLATE.format(c.URL_BASE, self._user_id),
                headers=self._ajax_headers,
                json={"code": code, "typeOf2FA": self._two_factor_method.value},
            ) as resp:
                json_rsp = await (resp.json())

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
                    url=self.LOGIN_2FA_TRUST_URL_TEMPLATE.format(
                        c.URL_BASE, self._user_id
                    ),
                    headers=self._ajax_headers,
                    json={"deviceName": device_name},
                ) as resp:
                    json_rsp = await (resp.json())
            except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                log.error("Can not load device trust page from Alarm.com")
                raise DataFetchFailed from err

            log.debug("Registered device.")

        # Save 2FA cookie value.
        for cookie in self._websession.cookie_jar:
            if cookie.key == self.LOGIN_TWO_FACTOR_COOKIE_NAME:
                log.debug("Found two-factor authentication cookie: %s", cookie.value)
                self._two_factor_cookie = (
                    {"twoFactorAuthenticationId": cookie.value} if cookie.value else {}
                )
                return str(cookie.value)

        log.error("Failed to find two-factor authentication cookie.")
        return None

    async def async_update(self, device_type: DeviceType | None = None) -> None:
        """Fetch latest device data."""

        log.debug("Calling update on Alarm.com")

        try:

            await self._async_get_trouble_conditions()

            device_types: list[DeviceType] = (
                [DeviceType.SYSTEM, device_type]
                if device_type
                else list(DEVICE_URLS["supported"].keys())
            )

            await self._async_get_and_build_devices(device_types)

        except (PermissionError, UnexpectedDataStructure) as err:
            raise err

    async def async_send_command(
        self,
        device_type: DeviceType,
        event: Lock.Command
        | Partition.Command
        | GarageDoor.Command
        | Light.Command
        | ImageSensor.Command,
        device_id: str | None = None,  # ID corresponds to device_type
        msg_body: dict | None = None,  # Body of request. No abstractions here.
        retry_on_failure: bool = True,  # Set to prevent infinite loops when function calls itself
    ) -> bool:
        """Send commands to Alarm.com."""
        log.debug("Sending %s to Alarm.com.", event)

        if not msg_body:
            msg_body = {}

        msg_body["statePollOnly"] = False

        url = (
            f"{DEVICE_URLS['supported'][device_type]['endpoint'].format(c.URL_BASE, device_id)}/{event.value}"
        )
        log.debug("Url %s", url)

        async with self._websession.post(
            url=url, json=msg_body, headers=self._ajax_headers
        ) as resp:

            log.debug("Response from Alarm.com %s", resp.status)
            if resp.status == 200:
                # Update alarm.com status after calling state change.
                await self.async_update(device_type)
                return True
            if resp.status == 423:
                # User has read-only permission to the entity.
                err_msg = (
                    f"{__name__}: User {self.user_email} has read-only access to"
                    f" {device_type.name.lower()} {device_id}."
                )
                raise PermissionError(err_msg)
            if (
                (resp.status == 422)
                and isinstance(event, Partition.Command)
                and (msg_body.get("forceBypass") is True)
            ):
                # 422 sometimes occurs when forceBypass is True but there's nothing to bypass.
                log.warning(
                    "Error executing %s, trying again without force bypass...",
                    event.value,
                )

                # Not changing retry_on_failure. Changing forcebypass means that we won't re-enter this block.

                msg_body["forceBypass"] = False

                return await self.async_send_command(
                    device_type, event, device_id, msg_body
                )
            if resp.status == 403:
                # May have been logged out, try again
                log.warning(
                    "Error executing %s, logging in and trying again...", event.value
                )
                if retry_on_failure:
                    await self.async_login()
                    return await self.async_send_command(
                        device_type,
                        event,
                        device_id,
                        msg_body,
                        False,
                    )

        log.error("%s failed with HTTP code %s", event.value, resp.status)
        log.error(
            """URL: %s
            JSON: %s
            Headers: %s""",
            url,
            msg_body,
            self._ajax_headers,
        )
        raise ConnectionError

    async def async_get_raw_server_responses(
        self,
        device_types: list[
            type[System]
            | type[Partition]
            | type[Sensor]
            | type[Lock]
            | type[GarageDoor]
            | type[ImageSensor]
            | type[Light]
            | type[Camera]
        ],
        include_image_sensor_b64: bool = False,
    ) -> dict:
        """Get raw responses from Alarm.com device endpoints."""

        return_data: dict = {}

        endpoints = []

        for device_type, device_data in (
            DEVICE_URLS["supported"] | DEVICE_URLS["unsupported"]
        ).items():
            if device_type in device_types:
                endpoints.append(
                    (slug_to_title(device_type.name), device_data["endpoint"])
                )

        if ImageSensor in device_types:
            endpoints.append(("Image Sensor Data", c.IMAGE_SENSOR_DATA_URL_TEMPLATE))

        for name, url_template in endpoints:

            async with self._websession.get(
                url=url_template.format(c.URL_BASE, ""),
                headers=self._ajax_headers,
            ) as resp:
                try:
                    json_rsp = await (resp.json())

                    if name == "Image Sensor Data" and not include_image_sensor_b64:
                        for image in json_rsp["data"]:
                            del image["attributes"]["image"]

                    rsp_errors = json_rsp.get("errors", [])

                    if len(rsp_errors) != 0:

                        error_msg = (
                            "async_get_raw_server_responses(): Failed to get data."
                            f" Response: {rsp_errors}"
                        )
                        log.debug(error_msg)

                        if rsp_errors[0].get("status") in ["403"]:
                            raise PermissionError(error_msg)

                        if (
                            rsp_errors[0].get("status") == "409"
                            and rsp_errors[0].get("detail")
                            == "TwoFactorAuthenticationRequired"
                        ):
                            raise AuthenticationFailed(error_msg)

                        if not (rsp_errors[0].get("status") in ["423"]):
                            # We'll get here if user doesn't have permission to access a specific device type.
                            pass

                    return_data[slug_to_title(name)] = (
                        "\n" + json.dumps(json_rsp) + "\n"
                    )

                except ContentTypeError:
                    if resp.status == 404:
                        return_data[slug_to_title(name)] = "Endpoint not found."
                    else:
                        return_data[
                            slug_to_title(name)
                        ] = f"\nUnprocessable output:\n{resp.text}\n"

        return return_data

    def get_device_by_id(
        self, device_id: str
    ) -> BaseDevice | System | Partition | Sensor | Lock | GarageDoor | ImageSensor | Light | Camera | None:
        """Find device by its id."""

        device: BaseDevice | System | Partition | Sensor | Lock | GarageDoor | ImageSensor | Light | Camera
        for device in (
            *self.systems,
            *self.partitions,
            *self.sensors,
            *self.locks,
            *self.garage_doors,
            *self.image_sensors,
            *self.lights,
            *self.cameras,
        ):
            if device.id_ == device_id:
                return device

        return None

    #
    #
    #####################
    # PRIVATE FUNCTIONS #
    #####################
    #
    # Help process data returned by the API

    async def _async_get_and_build_devices(
        self,
        device_types: list[DeviceType],
    ) -> None:
        """Get data for the specified device types and build objects."""

        for device_type in device_types:

            #
            # DETERMINE DEVICE'S PYALARMDOTCOMAJAX PYTHON CLASS
            #
            try:
                device_class: (
                    type[GarageDoor]
                    | type[Lock]
                    | type[Sensor]
                    | type[ImageSensor]
                    | type[Light]
                    | type[Partition]
                    | type[System]
                    | type[Camera]
                ) = DEVICE_CLASSES[device_type]

            except KeyError as err:
                raise UnsupportedDevice from err

            #############################
            # FETCH DATA FROM ALARM.COM #
            #############################

            #
            # GET ALL DEVICES WITHIN SPECIFIED CLASS
            #
            try:
                devices = await self._async_get_items_and_subordinates(
                    device_type=device_type
                )

            except BadAccount as err:
                # Indicates fatal account error.
                raise PermissionError from err

            if not devices:
                pass

            #
            # PURGE UNSUPPORTED CAMERAS
            #
            # This is a hack. We don't really support cameras (no images / streaming), we only support settings for the Skybell HD.
            if device_type == DeviceType.CAMERA:
                skybells: list = []
                for device_json, _ in devices:
                    if (
                        device_json.get("attributes", {}).get("deviceModel")
                        == "SKYBELLHD"
                    ):
                        skybells.append((device_json, None))

                devices = skybells
                if not devices:
                    pass

            #
            # MAKE ADDITIONAL CALLS IF REQUIRED FOR DEVICE TYPE
            #
            additional_endpoint_raw_results: dict = {}

            try:

                additional_endpoints: dict = DEVICE_URLS["supported"][device_type][
                    "additional_endpoints"
                ]

                for name, url in additional_endpoints.items():
                    additional_endpoint_raw_results[
                        name
                    ] = await self._async_get_items_and_subordinates(url=url)

            except KeyError:

                pass

            ####################
            # QUERY EXTENSIONS #
            ####################

            #
            # Check whether any devices have extensions.
            #

            required_extensions: list[type[CameraSkybellControllerExtension]] = []
            device_settings: dict[
                str, dict[str, ConfigurationOption]
            ] = {}  # device_id {slug: ConfigurationOption}
            name_id_map: dict[str, str] = {}

            #
            # Camera Skybell HD Extension
            # Skybell HD extension pulls data for all cameras at once. We can stop searching at the first hit since we only care if we have at least one.
            if device_type == DeviceType.CAMERA:
                for device_json, _ in devices:
                    if (
                        device_json.get("attributes", {}).get("deviceModel")
                        == "SKYBELLHD"
                    ):
                        required_extensions.append(CameraSkybellControllerExtension)
                        break

            #
            # Build map of device names -> device ids.
            #

            for device_json, subordinates in devices:
                if name := device_json.get("attributes", {}).get("description"):
                    name_id_map[name] = device_json["id"]

            #
            # Retrieve data for extensions
            #

            extension_controller: CameraSkybellControllerExtension | None = None

            for extension_class in required_extensions:

                extension_controller = extension_class(
                    websession=self._websession,
                    headers=self._ajax_headers,
                )

                # Fetch from Alarm.com
                extended_properties_list: list[
                    ExtendedProperties
                ] = await extension_controller.fetch()

                # Match extended properties to devices by name, then add to device_settings storage.
                for extended_property in extended_properties_list:
                    if (
                        device_name := extended_property.get("device_name")
                    ) in name_id_map:
                        device_id = name_id_map[device_name]
                        device_settings[device_id] = extended_property["settings"]

            ##############################
            # PREPROCESS ADDITIONAL DATA #
            ##############################

            #
            # PREPROCESSING FOR IMAGE SENSORS
            #
            # Extract recent images from image sensors

            element_specific_data: dict[str, ElementSpecificData] = {}

            if device_class is ImageSensor:
                for image in additional_endpoint_raw_results["recent_images"]:
                    if isinstance(image, dict) and (
                        image_sensor_id := str(
                            image.get("relationships", {})
                            .get("imageSensor", {})
                            .get("data", {})
                            .get("id")
                        )
                    ):

                        element_specific_data.setdefault(
                            image_sensor_id, {}
                        ).setdefault("raw_recent_images", set()).add(image)

            ###################
            # BASE PROCESSING #
            ###################

            temp_device_storage: list = []

            for device_raw_attribs, subordinates in devices:

                entity_id = device_raw_attribs["id"]

                entity_obj = device_class(
                    id_=entity_id,
                    raw_device_data=device_raw_attribs,
                    subordinates=subordinates,
                    element_specific_data=element_specific_data.get(entity_id),
                    send_action_callback=self.async_send_command,
                    config_change_callback=extension_controller.submit_change
                    if extension_controller
                    else None,
                    trouble_conditions=self._trouble_conditions.get(entity_id),
                    partition_id=self._partition_map.get(entity_id),
                    settings=device_settings.get(entity_id),
                )

                temp_device_storage.append(entity_obj)

            if device_class is System:
                self.systems[:] = temp_device_storage
            elif device_class is Partition:
                self.partitions[:] = temp_device_storage
            elif device_class is Sensor:
                self.sensors[:] = temp_device_storage
            elif device_class is GarageDoor:
                self.garage_doors[:] = temp_device_storage
            elif device_class is Lock:
                self.locks[:] = temp_device_storage
            elif device_class is Light:
                self.lights[:] = temp_device_storage
            elif device_class is ImageSensor:
                self.image_sensors[:] = temp_device_storage
            elif device_class is Camera:
                self.cameras[:] = temp_device_storage

    #
    #
    #################
    # API FUNCTIONS #
    #################
    #
    # Communicate directly with the ADC API

    async def _async_requires_2fa(self) -> bool | None:
        """Check whether two factor authentication is enabled on the account."""
        async with self._websession.get(
            url=DEVICE_URLS["supported"][DeviceType.SYSTEM]["endpoint"].format(
                c.URL_BASE, ""
            ),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await (resp.json())

        if (errors := json_rsp.get("errors")) and len(errors) > 0:
            for error in errors:
                if (
                    error.get("status") == "409"
                    and error.get("detail") == "TwoFactorAuthenticationRequired"
                ):
                    # Get 2FA type ID
                    async with self._websession.get(
                        url=self.LOGIN_2FA_DETAIL_URL_TEMPLATE.format(
                            c.URL_BASE, self._user_id
                        ),
                        headers=self._ajax_headers,
                    ) as resp:
                        json_rsp = await (resp.json())

                        if isinstance(
                            factor_id := json_rsp.get("data", {}).get("id"), int
                        ):
                            self._factor_type_id = factor_id
                            self._two_factor_method = OtpType(
                                json_rsp.get("data", {})
                                .get("attributes", {})
                                .get("twoFactorType")
                            )
                            log.debug(
                                "Requires 2FA. Using method %s", self._two_factor_method
                            )
                            return True

        log.debug("Does not require 2FA.")
        return False

    async def _async_get_identity_info(self) -> None:
        """Get user id, email address, provider name, etc."""
        try:
            async with self._websession.get(
                url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
                headers=self._ajax_headers,
                cookies=self._two_factor_cookie,
            ) as resp:
                json_rsp = await (resp.json())

                log.debug("Got identity info:\n%s", json.dumps(json_rsp))

                self._user_id = json_rsp["data"][0]["id"]
                self._provider_name = json_rsp["data"][0]["attributes"]["logoName"]

                for inclusion in json_rsp["included"]:
                    if (
                        inclusion["id"] == self._user_id
                        and inclusion["type"] == "profile/profile"
                    ):
                        self._user_email = inclusion["attributes"]["loginEmailAddress"]

            if self._user_email is None:
                raise AuthenticationFailed("Could not find user email address.")

            log.debug(
                "Got Provider: %s, User ID: %s", self._provider_name, self._user_id
            )

        except KeyError as err:
            log.debug(json_rsp)
            raise AuthenticationFailed from err

    async def _async_get_trouble_conditions(self) -> None:
        """Get trouble conditions for all devices."""
        try:
            async with self._websession.get(
                url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await (resp.json())

                log.debug("Got trouble conditions:\n%s", json_rsp)

                trouble_all_devices: dict = {}
                for condition in json_rsp.get("data", []):
                    new_trouble: TroubleCondition = {
                        "message_id": condition.get("id"),
                        "title": condition.get("attributes", {}).get("description"),
                        "body": condition.get("attributes", {})
                        .get("extraData", {})
                        .get("description"),
                        "device_id": (
                            device_id := condition.get("attributes", {}).get(
                                "emberDeviceId"
                            )
                        ),
                    }

                    trouble_single_device: list = trouble_all_devices.get(device_id, [])
                    trouble_single_device.append(new_trouble)
                    trouble_all_devices[device_id] = trouble_single_device

                self._trouble_conditions = trouble_all_devices

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Connection error while fetching trouble conditions.")
            raise DataFetchFailed from err

        except KeyError as err:
            log.error("Failed processing trouble conditions.")
            raise UnexpectedDataStructure from err

    # Takes EITHER url (without base) or device_type.
    async def _async_get_items_and_subordinates(
        self,
        device_type: DeviceType | None = None,
        url: str | None = None,
        retry_on_failure: bool = True,
    ) -> list:
        """Get attributes, metadata, and child devices for an ADC device class."""

        #
        # Determine URL
        #
        if (not device_type and not url) or (device_type and url):
            raise ValueError

        full_path = (
            DEVICE_URLS["supported"][device_type]["endpoint"] if device_type else url
        )

        #
        # Request data for device type
        #

        async with self._websession.get(
            url=full_path.format(c.URL_BASE, ""),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await (resp.json())

        return_items = []

        #
        # Handle Errors
        #

        rsp_errors = json_rsp.get("errors", [])
        if len(rsp_errors) != 0:

            error_msg = (
                "_async_get_items_and_subordinates(): Failed to get data for device"
                f" type {device_type}. Response: {rsp_errors}. Errors: {json_rsp}."
            )
            log.debug(error_msg)

            if rsp_errors[0].get("status") == "423":
                log.debug(
                    "Error fetching data from Alarm.com. This account either doesn't"
                    " have permission to %s, is on a plan that does not support %s, or"
                    " is part of a system with %s turned off.",
                    device_type,
                    device_type,
                    device_type,
                )
                # Carry on. We'll still try to load all other devices to which a user has access.
                return []

            if rsp_errors[0].get("status") == "403":
                # This could mean that we're logged out. Try logging in once, then assume bad credentials or some other issue.

                log.error("Error fetching data from Alarm.com.")

                if not retry_on_failure:
                    log.error("Giving up.")
                    raise BadAccount

                log.error("Trying to refresh auth tokens by logging in again.")

                await self.async_login()

                return await self._async_get_items_and_subordinates(
                    device_type=device_type,
                    retry_on_failure=False,
                )

            if (
                rsp_errors[0].get("status") == "409"
                and rsp_errors[0].get("detail") == "TwoFactorAuthenticationRequired"
            ):
                log.error(
                    "Failed while fetching items and subordinates. Two factor"
                    " authentication cookie is incorrect."
                )
                raise AuthenticationFailed(
                    "Failed while fetching items and subordinates. Two factor"
                    " authentication cookie is incorrect."
                )

            error_msg = (
                f"{__name__}: Showing first error only. Status:"
                f" {rsp_errors[0].get('status')}. Response: {json_rsp}"
            )
            log.debug(error_msg)
            raise DataFetchFailed(error_msg)

        #
        # Get child elements for partitions and systems if function called using device_type parameter.
        # If only url parameter used, we're probably just here to fetch additional endpoints.
        #

        if device_type and json_rsp.get("data"):
            try:
                for device in json_rsp["data"]:
                    # Get list of downstream devices. Add to list for reference
                    subordinates = []
                    if device_type in [
                        DeviceType.PARTITION,
                        DeviceType.SYSTEM,
                    ]:
                        for family_name, family_data in device["relationships"].items():

                            # TODO: Get list of unsupported devices to notify user of what has not been collected. Currently only collects known unknowns.
                            if DeviceType.has_value(family_name):

                                for sub_device in family_data["data"]:

                                    subordinates.append(
                                        (sub_device["id"], sub_device["type"])
                                    )

                                    if device_type == DeviceType.PARTITION:
                                        self._partition_map[sub_device["id"]] = device[
                                            "id"
                                        ]

                    return_items.append((device, subordinates))
            except KeyError as err:
                raise UnexpectedDataStructure(
                    f"Failed while processing {device_type}"
                ) from err

        return return_items

    async def _async_login_and_get_key(self) -> None:
        """Load hidden fields from login page."""
        try:
            # load login page once and grab VIEWSTATE/cookies
            async with self._websession.get(
                url=self.LOGIN_URL, cookies=self._two_factor_cookie
            ) as resp:
                text = await resp.text()
                log.debug("Response status from Alarm.com: %s", resp.status)
                tree = BeautifulSoup(text, "html.parser")
                login_info = {
                    self.VIEWSTATE_FIELD: tree.select(f"#{self.VIEWSTATE_FIELD}")[
                        0
                    ].attrs.get("value"),
                    self.VIEWSTATEGENERATOR_FIELD: tree.select(
                        f"#{self.VIEWSTATEGENERATOR_FIELD}"
                    )[0].attrs.get("value"),
                    self.EVENTVALIDATION_FIELD: tree.select(
                        f"#{self.EVENTVALIDATION_FIELD}"
                    )[0].attrs.get("value"),
                    self.PREVIOUSPAGE_FIELD: tree.select(f"#{self.PREVIOUSPAGE_FIELD}")[
                        0
                    ].attrs.get("value"),
                }

                log.debug(login_info)

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
                    self.VIEWSTATEGENERATOR_FIELD: login_info[
                        self.VIEWSTATEGENERATOR_FIELD
                    ],
                    self.EVENTVALIDATION_FIELD: login_info[self.EVENTVALIDATION_FIELD],
                    self.PREVIOUSPAGE_FIELD: login_info[self.PREVIOUSPAGE_FIELD],
                    "IsFromNewSite": "1",
                },
                cookies=self._two_factor_cookie,
            ) as resp:

                if re.search("m=login_fail", str(resp.url)) is not None:
                    log.error("Login failed.")
                    log.error("\nResponse URL:\n%s\n", str(resp.url))
                    log.error(
                        "\nRequest Headers:\n%s\n", str(resp.request_info.headers)
                    )
                    raise AuthenticationFailed("Invalid username and password.")

                # If Alarm.com is warning us that we'll have to set up two factor authentication soon, alert caller.
                if re.search("system-install", str(resp.url)) is not None:
                    raise NagScreen("Encountered 2FA nag screen.")

                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not login to Alarm.com")
            raise DataFetchFailed from err
        except KeyError as err:
            log.error("Unable to extract ajax key from Alarm.com. Response:\n%s", resp)
            raise DataFetchFailed from err

        log.debug("Logged in to Alarm.com.")
