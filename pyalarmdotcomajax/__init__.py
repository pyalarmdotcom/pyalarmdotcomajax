"""Alarmdotcom API Controller."""
from __future__ import annotations

import asyncio
import json
import logging
import re

import aiohttp
from aiohttp.client_exceptions import ContentTypeError
from bs4 import BeautifulSoup
from dateutil import parser

from .const import ADCDeviceType
from .const import ADCGarageDoorCommand
from .const import ADCImageSensorCommand
from .const import ADCLightCommand
from .const import ADCLockCommand
from .const import ADCOtpType
from .const import ADCPartitionCommand
from .const import ADCTroubleCondition
from .const import AuthResult
from .const import ElementSpecificData
from .const import ImageSensorElementSpecificData
from .const import TWO_FACTOR_COOKIE_NAME
from .entities import ADCGarageDoor
from .entities import ADCImageSensor
from .entities import ADCLight
from .entities import ADCLock
from .entities import ADCPartition
from .entities import ADCSensor
from .entities import ADCSystem
from .errors import AuthenticationFailed
from .errors import BadAccount
from .errors import DataFetchFailed
from .errors import DeviceTypeNotAuthorized
from .errors import NagScreen
from .errors import UnexpectedDataStructure
from .errors import UnsupportedDevice

__version__ = "0.2.10"


log = logging.getLogger(__name__)

DEVICE_TYPE_METADATA: dict = {
    "supported": {
        ADCDeviceType.GARAGE_DOOR: {
            "relationshipId": "devices/garage-door",
            "endpoint": "{}web/api/devices/garageDoors/{}",
            "device_class": ADCGarageDoor,
        },
        ADCDeviceType.IMAGE_SENSOR: {
            "relationshipId": "image-sensor/image-sensor",
            "endpoint": "{}web/api/imageSensor/imageSensors/{}",
            "device_class": ADCImageSensor,
            "additional_endpoints": {
                "recent_images": (
                    "{}/web/api/imageSensor/imageSensorImages/getRecentImages/{}"
                )
            },
        },
        ADCDeviceType.LIGHT: {
            "relationshipId": "devices/light",
            "endpoint": "{}web/api/devices/lights/{}",
            "device_class": ADCLight,
        },
        ADCDeviceType.LOCK: {
            "relationshipId": "devices/lock",
            "endpoint": "{}web/api/devices/locks/{}",
            "device_class": ADCLock,
        },
        ADCDeviceType.PARTITION: {
            "relationshipId": "devices/partition",
            "endpoint": "{}web/api/devices/partitions/{}",
            "device_class": ADCPartition,
        },
        ADCDeviceType.SENSOR: {
            "relationshipId": "devices/sensor",
            "endpoint": "{}web/api/devices/sensors/{}",
            "device_class": ADCSensor,
        },
        ADCDeviceType.SYSTEM: {
            "relationshipId": "systems/system",
            "endpoint": "{}web/api/systems/systems/{}",
            "device_class": ADCSystem,
        },
    },
    "unsupported": {
        ADCDeviceType.ACCESS_CONTROL: {
            "relationshipId": "devices/access-control-access-point-device",
            "endpoint": "{}web/api/devices/accessControlAccessPointDevices/{}",
        },
        ADCDeviceType.CAMERA: {
            "relationshipId": "video/camera",
            "endpoint": "{}web/api/video/cameras/{}",
        },
        ADCDeviceType.CAMERA_SD: {
            "relationshipId": "video/sd-card-camera",
            "endpoint": "{}web/api/video/sdCardCameras/{}",
        },
        ADCDeviceType.CAR_MONITOR: {
            "relationshipId": "devices/car-monitor",
            "endpoint": "{}web/api/devices/carMonitors{}",
        },
        ADCDeviceType.COMMERCIAL_TEMP: {
            "relationshipId": "devices/commercial-temperature-sensor",
            "endpoint": "{}web/api/devices/commercialTemperatureSensors/{}",
        },
        # ADCDeviceType.CONFIGURATION: {
        #     "relationshipId": "configuration",
        #     "endpoint": "{}web/api/systems/configurations/{}",
        # },
        # ADCDeviceType.FENCE: {
        #     "relationshipId": "",
        #     "endpoint": "{}web/api/geolocation/fences/{}",
        # },
        ADCDeviceType.GATE: {
            "relationshipId": "devices/gate",
            "endpoint": "{}web/api/devices/gates/{}",
        },
        ADCDeviceType.GEO_DEVICE: {
            "relationshipId": "geolocation/geo-device",
            "endpoint": "{}web/api/geolocation/geoDevices/{}",
        },
        ADCDeviceType.IQ_ROUTER: {
            "relationshipId": "devices/iq-router",
            "endpoint": "{}web/api/devices/iqRouters/{}",
        },
        ADCDeviceType.REMOTE_TEMP: {
            "relationshipId": "devices/remote-temperature-sensor",
            "endpoint": "{}web/api/devices/remoteTemperatureSensors/{}",
        },
        ADCDeviceType.SCENE: {
            "relationshipId": "automation/scene",
            "endpoint": "{}web/api/automation/scenes/{}",
        },
        ADCDeviceType.SHADE: {
            "relationshipId": "devices/shade",
            "endpoint": "{}web/api/devices/shades/{}",
        },
        ADCDeviceType.SMART_CHIME: {
            "relationshipId": "devices/smart-chime-device",
            "endpoint": "{}web/api/devices/smartChimeDevices/{}",
        },
        ADCDeviceType.SUMP_PUMP: {
            "relationshipId": "devices/sump-pump",
            "endpoint": "{}web/api/devices/sumpPumps/{}",
        },
        ADCDeviceType.SWITCH: {
            "relationshipId": "devices/switch",
            "endpoint": "{}web/api/devices/switches/{}",
        },
        ADCDeviceType.THERMOSTAT: {
            "relationshipId": "devices/thermostat",
            "endpoint": "{}web/api/devices/thermostats/{}",
        },
        ADCDeviceType.VALVE_SWITCH: {
            "relationshipId": "valve-switch",
            "endpoint": "{}web/api/devices/valveSwitches/{}",
        },
        ADCDeviceType.WATER_METER: {
            "relationshipId": "devices/water-meter",
            "endpoint": "{}web/api/devices/waterMeters/{}",
        },
        ADCDeviceType.WATER_SENSOR: {
            "relationshipId": "devices/water-sensor",
            "endpoint": "{}web/api/devices/waterSensors/{}",
        },
        ADCDeviceType.WATER_VALVE: {
            "relationshipId": "devices/water-valve",
            "endpoint": "{}web/api/devices/waterValves/{}",
        },
        ADCDeviceType.X10_LIGHT: {
            "relationshipId": "devices/x10light",
            "endpoint": "{}web/api/devices/x10Lights/{}",
        },
    },
}


class ADCController:
    """Base class for communicating with Alarm.com via API."""

    URL_BASE = "https://www.alarm.com/"

    # LOGIN & SESSION: BEGIN
    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"  # nosec
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
    LOGIN_2FA_POST_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/verifyTwoFactorCode"
    LOGIN_2FA_DETAIL_URL_TEMPLATE = (
        "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}"
    )
    LOGIN_2FA_TRUST_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/trustTwoFactorDevice"
    LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCode"
    LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaEmail"

    IDENTITIES_URL_TEMPLATE = "{}/web/api/identities/{}"
    IDENTITIES_2FA_NAG_URL_TEMPLATE = "{}system-install/api/identity"

    VIEWSTATE_FIELD = "__VIEWSTATE"
    VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
    EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
    PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

    KEEP_ALIVE_CHECK_URL_TEMPLATE = "{}web/KeepAlive.aspx?timestamp={}"
    KEEP_ALIVE_CHECK_RESPONSE = '{"status":"Keep Alive"}'
    KEEP_ALIVE_URL = "{}web/api/identities/{}/reloadContext"
    # LOGIN & SESSION: END

    # DEVICE MANAGEMENT: BEGIN
    PROVIDER_INFO_TEMPLATE = "{}/web/api/appload"
    TROUBLECONDITIONS_URL_TEMPLATE = (
        "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
    )
    IMAGE_SENSOR_DATA_URL_TEMPLATE = (
        "{}/web/api/imageSensor/imageSensorImages/getRecentImages"
    )
    # DEVICE MANAGEMENT: END

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        twofactorcookie: str | None = None,
    ):
        """Use AIOHTTP to make a request to alarm.com."""
        self._username: str = username
        self._password: str = password
        self._websession: aiohttp.ClientSession = websession
        self._ajax_headers = {
            "Accept": "application/vnd.api+json",
            "ajaxrequestuniquekey": None,
        }
        self._url_base: str = self.URL_BASE
        self._two_factor_cookie: dict = (
            {"twoFactorAuthenticationId": twofactorcookie} if twofactorcookie else {}
        )
        self._factor_type_id: int | None = None
        self._two_factor_method: ADCOtpType | None = None
        self._provider_name: str | None = None
        self._user_id: str | None = None
        self._user_email: str | None = None
        self._partition_map: dict = {}

        self._trouble_conditions: dict = {}

        self.systems: list[ADCSystem] = []
        self.partitions: list[ADCPartition] = []
        self.sensors: list[ADCSensor] = []
        self.locks: list[ADCLock] = []
        self.garage_doors: list[ADCGarageDoor] = []
        self.image_sensors: list[ADCImageSensor] = []
        self.lights: list[ADCLight] = []

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
        """Return user email address."""
        return (
            cookie
            if isinstance(self._two_factor_cookie, dict)
            and (cookie := self._two_factor_cookie.get(TWO_FACTOR_COOKIE_NAME))
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
                    ADCOtpType.SMS,
                    ADCOtpType.EMAIL,
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
                if self._two_factor_method == ADCOtpType.EMAIL
                else self.LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE
            )

            async with self._websession.post(
                url=request_url.format(self._url_base, self._user_id),
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
                url=self.LOGIN_2FA_POST_URL_TEMPLATE.format(
                    self._url_base, self._user_id
                ),
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
                        self._url_base, self._user_id
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
            if cookie.key == TWO_FACTOR_COOKIE_NAME:
                log.debug("Found two-factor authentication cookie: %s", cookie.value)
                self._two_factor_cookie = (
                    {"twoFactorAuthenticationId": cookie.value} if cookie.value else {}
                )
                return str(cookie.value)

        log.error("Failed to find two-factor authentication cookie.")
        return None

    async def async_update(self, device_type: ADCDeviceType | None = None) -> None:
        """Fetch the latest state according to device."""
        log.debug("Calling update on Alarm.com")

        try:

            await self._async_get_trouble_conditions()

            await self._async_get_devices(ADCDeviceType.SYSTEM, self.systems)

            if device_type in [ADCDeviceType.PARTITION, None]:
                await self._async_get_devices(ADCDeviceType.PARTITION, self.partitions)

            if device_type in [ADCDeviceType.SENSOR, None]:
                await self._async_get_devices(ADCDeviceType.SENSOR, self.sensors)

            if device_type in [ADCDeviceType.GARAGE_DOOR, None]:
                await self._async_get_devices(
                    ADCDeviceType.GARAGE_DOOR, self.garage_doors
                )

            if device_type == ADCDeviceType.LOCK or device_type is None:
                await self._async_get_devices(ADCDeviceType.LOCK, self.locks)

            if device_type == ADCDeviceType.LIGHT or device_type is None:
                await self._async_get_devices(ADCDeviceType.LIGHT, self.lights)

            if device_type in [ADCDeviceType.IMAGE_SENSOR, None]:
                await self._async_get_devices(
                    ADCDeviceType.IMAGE_SENSOR, self.image_sensors
                )

        except (PermissionError, UnexpectedDataStructure) as err:
            raise err

    #
    #
    ####################
    # HELPER FUNCTIONS #
    ####################
    #
    # Help process data returned by the API

    # Get functions build a new internal list of entities before assigning to their respective instance variables.
    # If we assign to the instance variable directly, the same elements will be added to the list every time we update.

    async def _async_get_devices(
        self,
        device_type: ADCDeviceType,
        device_storage: list,
    ) -> None:

        #
        # DETERMINE DEVICE'S PYALARMDOTCOMAJAX PYTHON CLASS
        #
        try:
            device_class: (
                type[ADCGarageDoor]
                | type[ADCLock]
                | type[ADCSensor]
                | type[ADCImageSensor]
                | type[ADCLight]
                | type[ADCPartition]
                | type[ADCSystem]
            ) = DEVICE_TYPE_METADATA["supported"][device_type]["device_class"]
        except KeyError as err:
            raise UnsupportedDevice from err

        #
        # GET ALL DEVICES WITHIN CLASS
        #
        try:
            entities = await self._async_get_items_and_subordinates(
                device_type=device_type
            )

        except BadAccount as err:
            # Indicates fatal account error.
            raise PermissionError from err

        except DeviceTypeNotAuthorized:
            # Indicates that device type is not supported but we should proceed with other types.
            # TODO: Bubble up notification that this device type is not supported so that the requesting script can stop asking for updates for this specific device type.
            return

        if not entities:
            return

        #
        # MAKE ADDITIONAL CALLS IF REQUIRED FOR DEVICE TYPE
        #
        additional_endpoint_raw_results: dict = {}

        try:

            additional_endpoints: dict = DEVICE_TYPE_METADATA["supported"][device_type][
                "additional_endpoints"
            ]

            for name, url in additional_endpoints.items():
                additional_endpoint_raw_results[
                    name
                ] = await self._async_get_items_and_subordinates(url=url)

        except KeyError:

            pass

        temp_device_storage = []

        for entity_json, subordinates in entities:

            entity_id = entity_json["id"]

            system_id = (
                entity_json.get("relationships", {})
                .get("system", {})
                .get("data", {})
                .get("id")
            )

            element_specific_data: ElementSpecificData | None = None

            #################
            # PREPROCESSING #
            #################

            #
            # PREPROCESSING FOR IMAGE SENSORS
            #
            # Extract recent images
            if device_class is ADCImageSensor:

                # Mypy wasn't happy when structured as a filter. Potential for stale entity_id.
                processed_image_data: list[ImageSensorElementSpecificData] = []
                for image in additional_endpoint_raw_results["recent_images"]:
                    if (
                        isinstance(image, dict)
                        and str(
                            image.get("relationships", {})
                            .get("imageSensor", {})
                            .get("data", {})
                            .get("id")
                        )
                        == entity_id
                    ):
                        image_data: ImageSensorElementSpecificData = {
                            "id_": image["id"],
                            "image_b64": image["attributes"]["image"],
                            "image_src": image["attributes"]["imageSrc"],
                            "description": image["attributes"]["description"],
                            "timestamp": parser.parse(image["attributes"]["timestamp"]),
                        }
                        processed_image_data.append(image_data)

                element_specific_data = {"images": processed_image_data}

            ###################
            # BASE PROCESSING #
            ###################

            #
            # BASE PROCESSING FOR SYSTEMS
            #

            if device_class is ADCSystem:

                parent_ids = {"system": system_id}

                # Construct representation of discovered partitions.
                entity_obj = device_class(
                    id_=entity_id,
                    attribs_raw=entity_json["attributes"],
                    family_raw=entity_json["type"],
                    send_action_callback=self.async_send,
                    subordinates=subordinates,
                    parent_ids=parent_ids,
                    trouble_conditions=self._trouble_conditions.get(entity_id),
                )

            #
            # BASE PROCESSING FOR PARTITIONS
            #

            if device_class is ADCPartition:

                parent_ids = {"system": system_id}

                # Construct representation of discovered partitions.
                entity_obj = device_class(
                    id_=entity_id,
                    attribs_raw=entity_json["attributes"],
                    family_raw=entity_json["type"],
                    send_action_callback=self.async_send,
                    subordinates=subordinates,
                    parent_ids=parent_ids,
                    trouble_conditions=self._trouble_conditions.get(entity_id),
                )

            #
            # BASE PROCESSING FOR ALL OTHER DEVICES
            #

            if device_class not in [ADCPartition, ADCSystem]:

                partition_id = self._partition_map.get(entity_id)
                parent_ids = {"system": system_id, "partition": partition_id}

                # Construct representation of discovered devices.

                entity_obj = device_class(
                    id_=entity_id,
                    attribs_raw=entity_json["attributes"],
                    family_raw=entity_json["type"],
                    subordinates=subordinates,
                    parent_ids=parent_ids,
                    element_specific_data=element_specific_data,
                    send_action_callback=self.async_send,
                    trouble_conditions=self._trouble_conditions.get(entity_id),
                )

            temp_device_storage.append(entity_obj)

        device_storage[:] = temp_device_storage

    #
    #
    #################
    # API FUNCTIONS #
    #################
    #
    # Communicate directly with the ADC API

    async def async_send(
        self,
        device_type: ADCDeviceType,
        event: ADCLockCommand
        | ADCPartitionCommand
        | ADCGarageDoorCommand
        | ADCLightCommand
        | ADCImageSensorCommand,
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
            f"{DEVICE_TYPE_METADATA['supported'][device_type]['endpoint'].format(self._url_base, device_id)}/{event.value}"
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
                and isinstance(event, ADCPartitionCommand)
                and (msg_body.get("forceBypass") is True)
            ):
                # 422 sometimes occurs when forceBypass is True but there's nothing to bypass.
                log.warning(
                    "Error executing %s, trying again without force bypass...",
                    event.value,
                )

                # Not changing retry_on_failure. Changing forcebypass means that we won't re-enter this block.

                msg_body["forceBypass"] = False

                return await self.async_send(device_type, event, device_id, msg_body)
            if resp.status == 403:
                # May have been logged out, try again
                log.warning(
                    "Error executing %s, logging in and trying again...", event.value
                )
                if retry_on_failure:
                    await self.async_login()
                    return await self.async_send(
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

    async def _async_requires_2fa(self) -> bool | None:
        """Check whether two factor authentication is enabled on the account."""
        async with self._websession.get(
            url=DEVICE_TYPE_METADATA["supported"][ADCDeviceType.SYSTEM][
                "endpoint"
            ].format(self._url_base, ""),
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
                            self._url_base, self._user_id
                        ),
                        headers=self._ajax_headers,
                    ) as resp:
                        json_rsp = await (resp.json())

                        if isinstance(
                            factor_id := json_rsp.get("data", {}).get("id"), int
                        ):
                            self._factor_type_id = factor_id
                            self._two_factor_method = ADCOtpType(
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
                url=self.IDENTITIES_URL_TEMPLATE.format(self._url_base, ""),
                headers=self._ajax_headers,
                cookies=self._two_factor_cookie,
            ) as resp:
                json_rsp = await (resp.json())

                log.debug("Got identity info:\n%s", json_rsp)

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
                url=self.TROUBLECONDITIONS_URL_TEMPLATE.format(self._url_base, ""),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await (resp.json())

                trouble_all_devices: dict = {}
                for condition in json_rsp.get("data", []):
                    new_trouble: ADCTroubleCondition = {
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

        except (KeyError) as err:
            log.error("Failed processing trouble conditions.")
            raise UnexpectedDataStructure from err

    # Takes EITHER url (without base) or device_type.
    async def _async_get_items_and_subordinates(
        self,
        device_type: ADCDeviceType | None = None,
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
            DEVICE_TYPE_METADATA["supported"][device_type]["endpoint"]
            if device_type
            else url
        )

        #
        # Request data for device type
        #

        async with self._websession.get(
            url=full_path.format(self._url_base, ""),
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

        if device_type:
            try:
                for device in json_rsp["data"]:
                    # Get list of downstream devices. Add to list for reference
                    subordinates = []
                    if device_type in [
                        ADCDeviceType.PARTITION,
                        ADCDeviceType.SYSTEM,
                    ]:
                        for family_name, family_data in device["relationships"].items():

                            # TODO: Get list of unsupported devices to notify user of what has not been collected. Currently only collects known unknowns.
                            if ADCDeviceType.has_value(family_name):

                                for sub_device in family_data["data"]:

                                    subordinates.append(
                                        (sub_device["id"], sub_device["type"])
                                    )

                                    # Individual devices don't list their associated partitions. We'll use this map to retrieve partition id when each device is created.
                                    if device_type == ADCDeviceType.PARTITION:
                                        self._partition_map[sub_device["id"]] = device[
                                            "id"
                                        ]

                    return_items.append((device, subordinates))
            except KeyError as err:
                raise UnexpectedDataStructure from err

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

    async def async_get_raw_server_responses(
        self,
        include_systems: bool = False,
        include_image_sensors: bool = False,
        include_unsupported: bool = False,
    ) -> str:
        """Get raw responses from Alarm.com device endpoints."""

        return_str: str = ""

        endpoints = [
            (
                device_type.name.replace("_", " ").title(),
                device_type_metadata["endpoint"],
            )
            for device_type, device_type_metadata in DEVICE_TYPE_METADATA[
                "supported"
            ].items()
            if device_type is not ADCDeviceType.SYSTEM
            and not include_systems
            and isinstance(device_type, ADCDeviceType)
        ]

        endpoints.append(("IMAGE_SENSORS_DATA", self.IMAGE_SENSOR_DATA_URL_TEMPLATE))

        if include_unsupported:
            endpoints += [
                (
                    device_type.name.replace("_", " ").title(),
                    device_type_metadata["endpoint"],
                )
                for device_type, device_type_metadata in DEVICE_TYPE_METADATA[
                    "unsupported"
                ].items()
                if device_type is not ADCDeviceType.SYSTEM
                and not include_systems
                and isinstance(device_type, ADCDeviceType)
            ]

        for name, url_template in endpoints:

            return_str += f"\n\n====[{name}]====\n\n"

            async with self._websession.get(
                url=url_template.format(self._url_base, ""),
                headers=self._ajax_headers,
            ) as resp:
                try:
                    json_rsp = await (resp.json())

                    if name == "IMAGE_SENSORS_DATA" and not include_image_sensors:
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

                    return_str += json.dumps(json_rsp)

                except ContentTypeError:
                    if resp.status == 404:
                        return_str += "Endpoint not found."
                    else:
                        return_str += f"Unprocessable output:\n{resp.text}"

        return return_str
