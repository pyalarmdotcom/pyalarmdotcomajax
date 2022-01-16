"""Alarmdotcom API Controller."""

# TODO: Add "debug" property that exports raw ADC responses. Useful for users who ask for support for devices not available to maintainers.

import asyncio
import logging
import re
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

from pyalarmdotcomajax.const import (
    ADCDeviceType,
    ADCGarageDoorCommand,
    ADCLockCommand,
    ADCPartitionCommand,
)
from pyalarmdotcomajax.entities import (
    ADCBaseElement,
    ADCGarageDoor,
    ADCLock,
    ADCPartition,
    ADCSensor,
    ADCSystem,
)
from pyalarmdotcomajax.errors import (
    AuthenticationFailed,
    DataFetchFailed,
    UnexpectedDataStructure,
    UnsupportedDevice,
)

__version__ = "0.2.12"

log = logging.getLogger(__name__)


class ADCController:
    """Base class for communicating with Alarm.com via API."""

    URL_BASE = "https://www.alarm.com/"

    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"

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

    TROUBLECONDITIONS_URL_TEMPLATE = (
        "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
    )

    def __init__(
        self,
        username: str,
        password: str,
        websession: aiohttp.ClientSession,
        forcebypass: bool,
        noentrydelay: bool,
        silentarming: bool,
        twofactorcookie: str,
    ):
        """Use AIOHTTP to make a request to alarm.com."""
        self._username = username
        self._password = password
        self._websession = websession
        self._ajax_headers = {
            "Accept": "application/vnd.api+json",
            "ajaxrequestuniquekey": None,
        }
        self._forcebypass = forcebypass  # "stay","away","true","false"
        self._noentrydelay = noentrydelay  # "stay","away","true","false"
        self._silentarming = silentarming  # "stay","away","true","false"
        self._url_base: str = self.URL_BASE
        self._twofactor_cookie: str = (
            {"twoFactorAuthenticationId": twofactorcookie} if twofactorcookie else {}
        )
        self._provider_name: str = None
        self._user_id: str = None
        self._user_email: str = None
        self._partition_map: dict = {}

        self.systems: list[ADCSystem] = []
        self.partitions: list[ADCPartition] = []
        self.sensors: list[ADCSensor] = []
        self.locks: list[ADCLock] = []
        self.garage_doors: list[ADCGarageDoor] = []

        self._init_hook()

    def _init_hook(self) -> None:
        """Let child classes do things during init without overriding the whole function."""
        pass

    #
    #
    ##############
    # PROPERTIES #
    ##############
    #
    #

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return self._provider_name

    @property
    def user_id(self) -> str:
        """Return user ID."""
        return self._user_id

    @property
    def user_email(self) -> str:
        """Return user email address."""
        return self._user_email

    #
    #
    ####################
    # PUBLIC FUNCTIONS #
    ####################
    #
    #

    async def async_login(self) -> bool:
        """Login to Alarm.com."""
        log.debug("Attempting to log in to Alarm.com")

        try:
            await self._async_login_and_get_key()
            await self._get_identity_info()
            await self.async_update()
        except (DataFetchFailed, UnexpectedDataStructure) as err:
            raise ConnectionError from err
        except (AuthenticationFailed, PermissionError) as err:
            raise AuthenticationFailed from err

    async def async_send_action(
        self,
        device_type: ADCDeviceType,
        event: ADCPartitionCommand or ADCLockCommand or ADCGarageDoorCommand,
        device_id: str,
    ) -> bool:
        """Send command to take action on device."""

        forcebypass: bool = None
        noentrydelay: bool = None
        silentarming: bool = None

        if event in [
            ADCPartitionCommand.ARM_AWAY,
            ADCPartitionCommand.ARM_STAY,
        ]:
            forcebypass = self._forcebypass in [
                "stay" if event == ADCPartitionCommand.ARM_AWAY else "away",
                "true",
            ]
            noentrydelay = self._noentrydelay in [
                "stay" if event == ADCPartitionCommand.ARM_AWAY else "away",
                "true",
            ]
            silentarming = self._silentarming in [
                "stay" if event == ADCPartitionCommand.ARM_AWAY else "away",
                "true",
            ]

        return await self._send(
            device_type,
            event,
            forcebypass,
            noentrydelay,
            silentarming,
            device_id,
        )

    async def async_update(self, device_type: ADCDeviceType = None) -> None:
        """Fetch the latest state according to device."""
        log.debug("Calling update on Alarm.com")

        try:
            await self._async_get_systems()

            if device_type == ADCDeviceType.PARTITION or device_type is None:
                await self._async_get_partitions()

            if device_type == ADCDeviceType.SENSOR or device_type is None:
                await self._async_get_devices(
                    ADCDeviceType.SENSOR, self.sensors, ADCSensor
                )

            if device_type == ADCDeviceType.GARAGE_DOOR or device_type is None:
                await self._async_get_devices(
                    ADCDeviceType.GARAGE_DOOR, self.garage_doors, ADCGarageDoor
                )

            if device_type == ADCDeviceType.LOCK or device_type is None:
                await self._async_get_devices(ADCDeviceType.LOCK, self.locks, ADCLock)
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
            )

            new_storage.append(entity_obj)

        device_storage[:] = new_storage

    async def _async_get_devices(
        self,
        device_type: ADCDeviceType,
        device_storage: list,
        device_class: ADCBaseElement,
    ) -> None:

        if device_type == ADCDeviceType.GARAGE_DOOR:
            url_template = self.GARAGE_DOOR_URL_TEMPLATE
        elif device_type == ADCDeviceType.LOCK:
            url_template = self.LOCK_URL_TEMPLATE
        elif device_type == ADCDeviceType.SENSOR:
            url_template = self.SENSOR_URL_TEMPLATE
        else:
            raise UnsupportedDevice

        new_storage = []

        entities = await self._async_get_items_and_subordinates(
            url_template, device_type
        )

        if not entities:
            return

        for entity_json, subordinates in entities:

            entity_id = entity_json["id"]

            system_id = (
                entity_json.get("relationships").get("system").get("data").get("id")
            )

            partition_id = self._partition_map.get(entity_id)

            parent_ids = {"system": system_id, "partition": partition_id}

            # Construct representation of discovered partitions.
            entity_obj = device_class(
                id_=entity_id,
                attribs_raw=entity_json["attributes"],
                family_raw=entity_json["type"],
                send_action_callback=self.async_send_action,
                subordinates=subordinates,
                parent_ids=parent_ids,
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
        event: ADCLockCommand or ADCPartitionCommand or ADCGarageDoorCommand,
        forcebypass: Optional[bool] = False,
        noentrydelay: Optional[bool] = False,
        silentarming: Optional[bool] = False,
        device_id: Optional[str] = None,  # ID corresponds to device_type
        retry_on_failure: Optional[
            bool
        ] = True,  # Set to prevent infinite loops when function calls itself
    ) -> bool:
        """Send commands to Alarm.com."""
        log.debug("Sending %s to Alarm.com.", event)
        if (
            device_type == ADCDeviceType.PARTITION
            and event != ADCPartitionCommand.DISARM
        ):
            json = {
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
            json = {"statePollOnly": False}

        # ################################
        # # BEGIN: SET URL BY DEVICE TYPE
        # #

        # PARTITION
        if device_type == ADCDeviceType.PARTITION:
            url = f"{self.PARTITION_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
            log.debug("Url %s", url)

        # LOCK
        elif device_type == ADCDeviceType.LOCK:
            url = f"{self.LOCK_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
            log.debug("Url %s", url)

        # GARAGE DOOR
        elif device_type == ADCDeviceType.GARAGE_DOOR:
            url = f"{self.GARAGE_DOOR_URL_TEMPLATE.format(self._url_base, device_id)}/{event.value}"
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
            json=json,
            headers=self._ajax_headers,
        ) as resp:
            log.debug("Response from Alarm.com %s", resp.status)
            if resp.status == 200:
                # Update alarm.com status after calling state change.
                await self.async_update(device_type)
                return True
            if resp.status == 423:
                # User has read-only permission to the entity.
                err_msg = f"{__name__}: User {self.user_email} has read-only access to {device_type.name.lower()} {device_id}."
                raise PermissionError(err_msg)
            elif resp.status == 403:
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
            json,
            self._ajax_headers,
        )
        raise ConnectionError

    async def _get_identity_info(self) -> None:
        async with self._websession.get(
            url=self.IDENTITIES_URL_TEMPLATE.format(self._url_base, ""),
            headers=self._ajax_headers,
        ) as resp:
            json = await (resp.json())

        try:
            self._user_id = json["data"][0]["id"]
            self._provider_name = json["data"][0]["attributes"]["logoName"]

            for inclusion in json["included"]:
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
            raise AuthenticationFailed from err

    async def _async_get_items_and_subordinates(
        self, url_template: str, device_type: ADCDeviceType.list()
    ) -> None:
        async with self._websession.get(
            url=url_template.format(self._url_base, ""),
            headers=self._ajax_headers,
        ) as resp:
            json = await (resp.json())

        return_items = []

        rsp_errors = json.get("errors", [])
        if len(rsp_errors) != 0:
            log.debug(
                "Failed to get data for device type %s. Response: %s",
                device_type,
                rsp_errors,
            )
            if rsp_errors[0].get("status") == "423":
                # TODO: This probably means that we're logged out. Should we log back in?
                raise PermissionError
            else:
                raise DataFetchFailed

        try:
            for device in json["data"]:
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

    async def _async_login_and_get_key(self) -> bool:
        """Load hidden fields from login page."""
        try:
            # load login page once and grab VIEWSTATE/cookies
            async with self._websession.get(
                url=self.LOGIN_URL, cookies=self._twofactor_cookie
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
                log.info("Attempting login to Alarm.com")
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
                cookies=self._twofactor_cookie,
            ) as resp:
                if re.search("m=login_fail", str(resp.url)) is not None:
                    raise AuthenticationFailed("Invalid username and password.")
                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            log.error("Can not login to Alarm.com")
            raise DataFetchFailed from err
        except KeyError as err:
            log.error("Unable to extract ajax key from Alarm.com")
            log.debug("Response: %s", resp)
            raise DataFetchFailed from err
