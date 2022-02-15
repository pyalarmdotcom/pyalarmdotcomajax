"""Alarmdotcom API Controller."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Literal

import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser

from .const import (
    TWO_FACTOR_COOKIE_NAME,
    ADCDeviceType,
    ADCGarageDoorCommand,
    ADCImageSensorCommand,
    ADCLockCommand,
    ADCPartitionCommand,
    ADCTroubleCondition,
    ArmingOption,
    AuthResult,
    ElementSpecificData,
    ImageData,
)
from .entities import (
    ADCGarageDoor,
    ADCImageSensor,
    ADCLock,
    ADCPartition,
    ADCSensor,
    ADCSystem,
)
from .errors import (
    AuthenticationFailed,
    BadAccount,
    DataFetchFailed,
    DeviceTypeNotAuthorized,
    NagScreen,
    UnexpectedDataStructure,
    UnsupportedDevice,
)

__version__ = "0.2.0"


log = logging.getLogger(__name__)


class ADCController:
    """Base class for communicating with Alarm.com via API."""

    URL_BASE = "https://www.alarm.com/"

    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"  # nosec
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
    LOGIN_2FA_POST_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/verifyTwoFactorCode"
    LOGIN_2FA_DETAIL_URL_TEMPLATE = (
        "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}"
    )
    LOGIN_2FA_TRUST_URL_TEMPLATE = "{}web/api/twoFactorAuthentication/twoFactorAuthentications/{}/trustTwoFactorDevice"

    VIEWSTATE_FIELD = "__VIEWSTATE"
    VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
    EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
    PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

    PROVIDER_INFO_TEMPLATE = "{}/web/api/appload"
    SYSTEM_URL_TEMPLATE = "{}web/api/systems/systems/{}"
    PARTITION_URL_TEMPLATE = "{}web/api/devices/partitions/{}"
    LOCK_URL_TEMPLATE = "{}web/api/devices/locks/{}"
    SENSOR_URL_TEMPLATE = "{}web/api/devices/sensors/{}"
    GARAGE_DOOR_URL_TEMPLATE = "{}web/api/devices/garageDoors/{}"
    LOCK_URL_TEMPLATE = "{}web/api/devices/locks/{}"
    IDENTITIES_URL_TEMPLATE = "{}/web/api/identities/{}"
    IDENTITIES_2FA_NAG_URL_TEMPLATE = "{}system-install/api/identity"
    IMAGE_SENSOR_URL_TEMPLATE = "{}/web/api/imageSensor/imageSensors/{}"
    IMAGE_SENSOR_DATA_URL_TEMPLATE = (
        "{}/web/api/imageSensor/imageSensorImages/getRecentImages"
    )

    KEEP_ALIVE_CHECK_URL_TEMPLATE = "{}web/KeepAlive.aspx?timestamp={}"
    KEEP_ALIVE_CHECK_RESPONSE = '{"status":"Keep Alive"}'
    KEEP_ALIVE_URL = "{}web/api/identities/{}/reloadContext"

    # Unsupported
    THERMOSTAT_URL_TEMPLATE = "{}web/api/devices/thermostats/{}"
    LIGHT_URL_TEMPLATE = "{}web/api/devices/lights/{}"
    CAMERA_URL_TEMPLATE = "{}web/api/video/cameras/{}"

    TROUBLECONDITIONS_URL_TEMPLATE = (
        "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
    )

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        twofactorcookie: str | None,
        forcebypass: ArmingOption = ArmingOption.NEVER,
        noentrydelay: ArmingOption = ArmingOption.NEVER,
        silentarming: ArmingOption = ArmingOption.NEVER,
    ):
        """Use AIOHTTP to make a request to alarm.com."""
        self._username = username
        self._password = password
        self._websession = websession
        self._ajax_headers = {
            "Accept": "application/vnd.api+json",
            "ajaxrequestuniquekey": None,
        }
        self._forcebypass = forcebypass
        self._noentrydelay = noentrydelay
        self._silentarming = silentarming
        self._url_base: str = self.URL_BASE
        self._two_factor_cookie: dict = (
            {"twoFactorAuthenticationId": twofactorcookie} if twofactorcookie else {}
        )
        self._factor_type_id: int | None = None
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

    async def async_login(self) -> AuthResult:
        """Login to Alarm.com."""
        log.debug("Attempting to log in to Alarm.com")

        try:
            await self._async_login_and_get_key()
            await self._async_get_identity_info()

            if not self._two_factor_cookie and await self._async_requires_2fa():
                log.debug("Two factor authentication code or cookie required.")
                return AuthResult.OTP_REQUIRED

        except (DataFetchFailed, UnexpectedDataStructure) as err:
            raise ConnectionError from err
        except (AuthenticationFailed, PermissionError) as err:
            raise AuthenticationFailed from err
        except NagScreen:
            return AuthResult.ENABLE_TWO_FACTOR

        return AuthResult.SUCCESS

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

            async with self._websession.post(
                url=self.LOGIN_2FA_POST_URL_TEMPLATE.format(
                    self._url_base, self._user_id
                ),
                headers=self._ajax_headers,
                json={"code": code, "typeOf2FA": 1},
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

    async def async_send_action(
        self,
        device_type: ADCDeviceType,
        event: ADCPartitionCommand
        | ADCLockCommand
        | ADCGarageDoorCommand
        | ADCImageSensorCommand,
        device_id: str,
    ) -> bool:
        """Send command to take action on device."""

        forcebypass: bool = False
        noentrydelay: bool = False
        silentarming: bool = False

        if event in [
            ADCPartitionCommand.ARM_AWAY,
            ADCPartitionCommand.ARM_STAY,
        ]:
            forcebypass = self._forcebypass in [
                ArmingOption.STAY
                if event == ADCPartitionCommand.ARM_STAY
                else ArmingOption.AWAY,
                ArmingOption.ALWAYS,
            ]
            noentrydelay = self._noentrydelay in [
                ArmingOption.STAY
                if event == ADCPartitionCommand.ARM_STAY
                else ArmingOption.AWAY,
                ArmingOption.ALWAYS,
            ]
            silentarming = self._silentarming in [
                ArmingOption.STAY
                if event == ADCPartitionCommand.ARM_STAY
                else ArmingOption.AWAY,
                ArmingOption.ALWAYS,
            ]

        return await self._send(
            device_type,
            event,
            forcebypass,
            noentrydelay,
            silentarming,
            device_id,
        )

    async def async_update(self, device_type: ADCDeviceType | None = None) -> None:
        """Fetch the latest state according to device."""
        log.debug("Calling update on Alarm.com")

        try:
            await self._async_get_trouble_conditions()

            await self._async_get_systems()

            if device_type in [ADCDeviceType.PARTITION, None]:
                await self._async_get_partitions()

            if device_type in [ADCDeviceType.SENSOR, None]:
                await self._async_get_devices(ADCDeviceType.SENSOR, self.sensors)

            if device_type in [ADCDeviceType.GARAGE_DOOR, None]:
                await self._async_get_devices(
                    ADCDeviceType.GARAGE_DOOR, self.garage_doors
                )

            if device_type == ADCDeviceType.LOCK or device_type is None:
                await self._async_get_devices(ADCDeviceType.LOCK, self.locks)

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

    async def _async_get_systems(self) -> None:

        device_type = ADCDeviceType.SYSTEM
        device_storage = self.systems
        device_class = ADCSystem

        new_storage = []

        entities = await self._async_get_items_and_subordinates(
            self.SYSTEM_URL_TEMPLATE, device_type
        )

        if not entities:
            log.debug("%s: No entities returned.", __name__)
            return

        for entity_json, subordinates in entities:
            # Construct representation of discovered entities.
            entity_obj = device_class(
                id_=entity_json["id"],
                attribs_raw=entity_json["attributes"],
                family_raw=entity_json["type"],
                send_action_callback=self.async_send_action,
                subordinates=subordinates,
                trouble_conditions=self._trouble_conditions.get(entity_json["id"]),
            )

            new_storage.append(entity_obj)

        device_storage[:] = new_storage

    async def _async_get_partitions(self) -> None:

        device_type = ADCDeviceType.PARTITION
        device_storage = self.partitions
        device_class = ADCPartition

        new_storage = []

        entities = await self._async_get_items_and_subordinates(
            self.PARTITION_URL_TEMPLATE, device_type
        )

        if not entities:
            return

        for entity_json, subordinates in entities:

            system_id = (
                entity_json.get("relationships").get("system").get("data").get("id")
            )

            parent_ids = {"system": system_id}

            # Construct representation of discovered partitions.
            entity_obj = device_class(
                id_=entity_json["id"],
                attribs_raw=entity_json["attributes"],
                family_raw=entity_json["type"],
                send_action_callback=self.async_send_action,
                subordinates=subordinates,
                parent_ids=parent_ids,
                trouble_conditions=self._trouble_conditions.get(entity_json["id"]),
            )

            new_storage.append(entity_obj)

        device_storage[:] = new_storage

    async def _async_get_devices(
        self,
        device_type: ADCDeviceType,
        device_storage: list,
    ) -> None:

        device_class: type[ADCGarageDoor] | type[ADCLock] | type[ADCSensor] | type[
            ADCImageSensor
        ]

        if device_type == ADCDeviceType.GARAGE_DOOR:
            url_template = self.GARAGE_DOOR_URL_TEMPLATE
            device_class = ADCGarageDoor
        elif device_type == ADCDeviceType.LOCK:
            url_template = self.LOCK_URL_TEMPLATE
            device_class = ADCLock
        elif device_type == ADCDeviceType.SENSOR:
            url_template = self.SENSOR_URL_TEMPLATE
            device_class = ADCSensor
        elif device_type == ADCDeviceType.IMAGE_SENSOR:
            url_template = self.IMAGE_SENSOR_URL_TEMPLATE
            device_class = ADCImageSensor
        else:
            raise UnsupportedDevice

        new_storage = []

        try:
            entities = await self._async_get_items_and_subordinates(
                url_template, device_type
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

        for entity_json, subordinates in entities:
            entity_id: str = str(entity_json["id"])

            system_id: str = (
                entity_json.get("relationships", {})
                .get("system", {})
                .get("data", {})
                .get("id")
            )

            partition_id = self._partition_map.get(entity_id)

            parent_ids = {"system": system_id, "partition": partition_id}

            element_specific_data: ElementSpecificData | None = None

            # Construct representation of discovered devices.
            if device_class == ADCImageSensor:
                image_data_raw = await self.async_get_raw_server_response(
                    "IMAGE_SENSORS_DATA",
                )

                # Mypy wasn't happy when structured as a filter. Potential for stale entity_id.
                processed_image_data: list[ImageData] = []
                for image in image_data_raw:
                    if (
                        str(
                            image.get("relationships", {})
                            .get("imageSensor", {})
                            .get("data", {})
                            .get("id")
                        )
                        == entity_id
                    ):
                        image_data: ImageData = {
                            "id_": image["id"],
                            "image_b64": image["attributes"]["image"],
                            "image_src": image["attributes"]["imageSrc"],
                            "description": image["attributes"]["description"],
                            "timestamp": parser.parse(image["attributes"]["timestamp"]),
                        }
                        processed_image_data.append(image_data)

                element_specific_data = {"images": processed_image_data}

            entity_obj = device_class(
                id_=entity_id,
                attribs_raw=entity_json["attributes"],
                family_raw=entity_json["type"],
                send_action_callback=self.async_send_action,
                subordinates=subordinates,
                parent_ids=parent_ids,
                element_specific_data=element_specific_data,
                trouble_conditions=self._trouble_conditions.get(entity_json["id"]),
            )

            new_storage.append(entity_obj)

        device_storage[:] = new_storage

    #
    #
    #################
    # API FUNCTIONS #
    #################
    #
    # Communicate directly with the ADC API

    async def _send(
        self,
        device_type: ADCDeviceType,
        event: ADCLockCommand
        | ADCPartitionCommand
        | ADCGarageDoorCommand
        | ADCImageSensorCommand,
        forcebypass: bool = False,
        noentrydelay: bool = False,
        silentarming: bool = False,
        device_id: str | None = None,  # ID corresponds to device_type
        retry_on_failure: bool = True,  # Set to prevent infinite loops when function calls itself
    ) -> bool:
        """Send commands to Alarm.com."""
        log.debug("Sending %s to Alarm.com.", event)
        if (
            device_type == ADCDeviceType.PARTITION
            and event != ADCPartitionCommand.DISARM
        ):
            json_req = {
                "statePollOnly": False,
                **{
                    key: value
                    for key, value in {
                        "forceBypass": forcebypass,
                        "noEntryDelay": noentrydelay,
                        "silentArming": silentarming,
                    }.items()
                    if value is True
                },
            }
        else:
            json_req = {"statePollOnly": False}

        # ################################
        # # BEGIN: SET URL BY DEVICE TYPE
        # #

        # PARTITION
        if device_type == ADCDeviceType.PARTITION:
            url = (
                f"{self.PARTITION_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
            )
            log.debug("Url %s", url)

        # LOCK
        elif device_type == ADCDeviceType.LOCK:
            url = (
                f"{self.LOCK_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
            )
            log.debug("Url %s", url)

        # GARAGE DOOR
        elif device_type == ADCDeviceType.GARAGE_DOOR:
            url = (
                f"{self.GARAGE_DOOR_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
            )
            log.debug("Url %s", url)

        # IMAGE SENSORS
        elif device_type == ADCDeviceType.IMAGE_SENSOR:
            url = (
                f"{self.IMAGE_SENSOR_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
            )
            log.debug("Url %s", url)

        # UNSUPPORTED
        else:
            log.debug("%s device type not supported.", device_type)
            raise UnsupportedDevice(f"{device_type} device type not supported.")

        # #
        # # END: SET URL BY DEVICE TYPE
        # ##############################

        async with self._websession.post(
            url=url,
            json=json_req,
            headers=self._ajax_headers,
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
                and (forcebypass is True)
            ):
                # 422 sometimes occurs when forceBypass is True but there's nothing to bypass.
                log.warning(
                    "Error executing %s, trying again without force bypass...",
                    event.value,
                )

                # Not changing retry_on_failure. Changing forcebypass means that we won't re-enter this block.
                return await self._send(
                    device_type,
                    event,
                    False,
                    noentrydelay,
                    silentarming,
                    device_id,
                )
            if resp.status == 403:
                # May have been logged out, try again
                log.warning(
                    "Error executing %s, logging in and trying again...", event.value
                )
                if retry_on_failure:
                    await self.async_login()
                    return await self._send(
                        device_type,
                        event,
                        forcebypass,
                        noentrydelay,
                        silentarming,
                        device_id,
                        False,
                    )

        log.error("%s failed with HTTP code %s", event.value, resp.status)
        log.error(
            """Arming parameters: force_bypass = %s, no_entry_delay = %s, silent_arming = %s
            URL: %s
            JSON: %s
            Headers: %s""",
            forcebypass,
            noentrydelay,
            silentarming,
            url,
            json_req,
            self._ajax_headers,
        )
        raise ConnectionError

    async def _async_requires_2fa(self) -> bool | None:
        """Check whether two factor authentication is enabled on the account."""
        async with self._websession.get(
            url=self.SYSTEM_URL_TEMPLATE.format(self._url_base, ""),
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
                            log.debug("Requires 2FA.")
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

    async def _async_get_items_and_subordinates(
        self,
        url_template: str,
        device_type: Literal[ADCDeviceType.SYSTEM]
        | Literal[ADCDeviceType.SENSOR]
        | Literal[ADCDeviceType.PARTITION]
        | Literal[ADCDeviceType.LOCK]
        | Literal[ADCDeviceType.GARAGE_DOOR]
        | Literal[ADCDeviceType.IMAGE_SENSOR],
        retry_on_failure: bool = True,
    ) -> list:
        """Get attributes, metadata, and child devices for an ADC device class."""
        async with self._websession.get(
            url=url_template.format(self._url_base, ""),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp = await (resp.json())

        return_items = []

        rsp_errors = json_rsp.get("errors", [])
        if len(rsp_errors) != 0:

            error_msg = (
                f"Failed to get data for device type {device_type}. Response:"
                f" {rsp_errors}. Errors: {json_rsp}."
            )
            log.debug(error_msg)

            if rsp_errors[0].get("status") == "423":
                log.debug(
                    "Error fetching data from Alarm.com. This account either doesn't"
                    " have permission to %s or is on a plan that does not support %s.",
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
                    url_template=url_template,
                    device_type=device_type,
                    retry_on_failure=True,
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

        try:
            for device in json_rsp["data"]:
                # Get list of downstream devices. Add to list for reference
                subordinates = []
                if device_type in [
                    ADCDeviceType.PARTITION,
                    ADCDeviceType.SYSTEM,
                ]:
                    for family_name, family_data in device["relationships"].items():
                        # TODO: Get list of unsupported devices to notify user of what has not been collected.
                        if ADCDeviceType.has_value(family_name):
                            for sub_device in family_data["data"]:
                                subordinates.append(
                                    (sub_device["id"], sub_device["type"])
                                )

                                # Individual devices don't list their associated partitions. We'll use this map to retrieve partition id when each device is created.
                                if device_type == ADCDeviceType.PARTITION:
                                    self._partition_map[sub_device["id"]] = device["id"]

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

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not load login page from Alarm.com")
            raise DataFetchFailed from err
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
                    raise AuthenticationFailed("Invalid username and password.")

                # If Alarm.com is warning us that we'll have to set up two factor authentication soon, alert caller.
                if re.search("system-install", str(resp.url)) is not None:
                    raise NagScreen("Encountered 2FA nag screen.")

                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not login to Alarm.com")
            raise DataFetchFailed from err
        except KeyError as err:
            log.error("Unable to extract ajax key from Alarm.com")
            log.debug("Response: %s", resp)
            raise DataFetchFailed from err

        logging.debug("Logged in to Alarm.com.")

    async def async_get_raw_server_responses(
        self, include_systems: bool = False, include_unsupported: bool = False
    ) -> str:
        """Get raw responses from Alarm.com device endpoints."""

        return_str: str = ""

        endpoints = [
            ("LOCKS", self.LOCK_URL_TEMPLATE),
            ("SENSORS", self.SENSOR_URL_TEMPLATE),
            ("GARAGE_DOORS", self.GARAGE_DOOR_URL_TEMPLATE),
            ("PARTITIONS", self.PARTITION_URL_TEMPLATE),
            ("IMAGE_SENSORS_DATA", self.IMAGE_SENSOR_DATA_URL_TEMPLATE),
        ]

        if include_systems:
            endpoints.append(("SYSTEMS", self.SYSTEM_URL_TEMPLATE))

        if include_unsupported:
            endpoints += [
                ("THERMOSTATS", self.THERMOSTAT_URL_TEMPLATE),
                ("LIGHTS", self.LIGHT_URL_TEMPLATE),
                ("CAMERAS", self.CAMERA_URL_TEMPLATE),
            ]

        for name, url_template in endpoints:

            return_str += f"\n\n====[{name}]====\n\n"

            async with self._websession.get(
                url=url_template.format(self._url_base, ""),
                headers=self._ajax_headers,
            ) as resp:
                json_rsp = await (resp.json())

            rsp_errors = json_rsp.get("errors", [])
            if len(rsp_errors) != 0:

                error_msg = f"Failed to get data. Response: {rsp_errors}"
                log.debug(error_msg)

                if rsp_errors[0].get("status") in ["403"]:
                    raise PermissionError(error_msg)
                elif (
                    rsp_errors[0].get("status") == "409"
                    and rsp_errors[0].get("detail") == "TwoFactorAuthenticationRequired"
                ):
                    raise AuthenticationFailed(error_msg)

                if not (rsp_errors[0].get("status") in ["423"]):
                    raise DataFetchFailed(error_msg)

            return_str += json.dumps(json_rsp)

        return return_str

    async def async_get_raw_server_response(
        self,
        endpoint: str,
        include_systems: bool = False,
        include_unsupported: bool = False,
    ) -> dict:
        """Get raw responses from specific Alarm.com device endpoint."""

        endpoints = {
            "LOCKS": self.LOCK_URL_TEMPLATE,
            "SENSORS": self.SENSOR_URL_TEMPLATE,
            "GARAGE_DOORS": self.GARAGE_DOOR_URL_TEMPLATE,
            "PARTITIONS": self.PARTITION_URL_TEMPLATE,
            "IMAGE_SENSORS_DATA": self.IMAGE_SENSOR_DATA_URL_TEMPLATE,
        }

        if include_systems:
            endpoints["SYSTEMS"] = self.SYSTEM_URL_TEMPLATE

        if include_unsupported:
            endpoints["THERMOSTATS"] = self.THERMOSTAT_URL_TEMPLATE
            endpoints["LIGHTS"] = self.LIGHT_URL_TEMPLATE
            endpoints["CAMERAS"] = self.CAMERA_URL_TEMPLATE

        url_template = endpoints[endpoint]

        async with self._websession.get(
            url=url_template.format(self._url_base, ""),
            headers=self._ajax_headers,
        ) as resp:
            json_rsp: dict = await (resp.json())

        rsp_errors = json_rsp.get("errors", [])
        if len(rsp_errors) != 0:
            error_msg = f"Failed to get data. Response: {rsp_errors}"
            log.debug(error_msg)

            if rsp_errors[0].get("status") in ["403"]:
                raise PermissionError(error_msg)
            elif (
                rsp_errors[0].get("status") == "409"
                and rsp_errors[0].get("detail") == "TwoFactorAuthenticationRequired"
            ):
                raise AuthenticationFailed(error_msg)

            if not (rsp_errors[0].get("status") in ["423"]):
                raise DataFetchFailed(error_msg)

        json_data: dict = json_rsp["data"]
        return json_data
