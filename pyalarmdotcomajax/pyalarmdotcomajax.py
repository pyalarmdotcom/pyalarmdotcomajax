"""pyalarmdotcomajax module."""
import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


class Alarmdotcom:
    """
    Access to alarm.com partners and accounts.

    This class is used to interface with the options available through
    alarm.com. The basic functions of checking system status and arming
    and disarming the system are possible.
    """

    URL_BASE = "https://www.alarm.com/"
    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
    VIEWSTATE_FIELD = "__VIEWSTATE"
    VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
    EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
    PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"
    SYSTEMITEMS_URL = "https://www.alarm.com/web/api/systems/availableSystemItems"
    SYSTEM_URL_TEMPLATE = "{}web/api/systems/systems/{}"
    PARTITION_URL_TEMPLATE = "{}web/api/devices/partitions/{}"
    TROUBLECONDITIONS_URL_TEMPLATE = (
        "{}web/api/troubleConditions/troubleConditions?forceRefresh=false"
    )
    SENSOR_STATUS_URL_TEMPLATE = "{}web/api/devices/sensors"
    THERMOSTAT_STATUS_URL_TEMPLATE = "{}web/api/devices/thermostats"
    GARAGE_DOOR_STATUS_URL_TEMPLATE = "{}web/api/devices/garageDoors"
    STATEMAP = (
        "",
        "disarmed",
        "armed stay",
        "armed away",
    )  # index is ADC's json status, value is integration's status
    GARAGE_DOOR_STATEMAP = (
        "Transitioning",  # 0
        "Open",  # 1
        "Closed",  # 2
    )
    COMMAND_LIST = {
        "Disarm": {"command": "disarm"},
        "Arm+Stay": {"command": "armStay"},
        "Arm+Away": {"command": "armAway"},
    }
    THERMOSTAT_ATTRIBUTES = (
        "ambientTemp",
        "coolSetpoint",
        "fanMode",
        "heatSetpoint",
        "humidityLevel",
        "state",
    )

    def __init__(
        self,
        username,
        password,
        websession,
        forcebypass,
        noentrydelay,
        silentarming,
        twofactorcookie,
    ):
        """
        Use aiohttp to make a request to alarm.com

        :param username: Alarm.com username
        :param password: Alarm.com password
        :param websession: AIOHttp Websession
        :param loop: Async loop.
        """
        self._username = username
        self._password = password
        self._websession = websession
        self.state = ""  # empty string instead of None
        self.sensor_status = None
        self._ajax_headers = {
            "Accept": "application/vnd.api+json",
            "ajaxrequestuniquekey": None,
        }
        self._systemid = None
        self._partitionid = None
        self._forcebypass = forcebypass  # "stay","away","true","false"
        self._noentrydelay = noentrydelay  # "stay","away","true","false"
        self._silentarming = silentarming  # "stay","away","true","false"
        self._thermostat_detected = False
        self._garage_door_detected = False
        self._url_base = self.URL_BASE
        self._twofactor_cookie = (
            {"twoFactorAuthenticationId": twofactorcookie} if twofactorcookie else {}
        )

    async def _async_get_ajax_key(self):
        try:
            # load login page once and grab VIEWSTATE/cookies
            async with self._websession.get(
                url=self.LOGIN_URL, cookies=self._twofactor_cookie
            ) as resp:
                text = await resp.text()
                _LOGGER.debug("Response status from Alarm.com: %s", resp.status)
                tree = BeautifulSoup(text, "html.parser")
                login_info = {
                    self.VIEWSTATE_FIELD: tree.select(
                        "#{}".format(self.VIEWSTATE_FIELD)
                    )[0].attrs.get("value"),
                    self.VIEWSTATEGENERATOR_FIELD: tree.select(
                        "#{}".format(self.VIEWSTATEGENERATOR_FIELD)
                    )[0].attrs.get("value"),
                    self.EVENTVALIDATION_FIELD: tree.select(
                        "#{}".format(self.EVENTVALIDATION_FIELD)
                    )[0].attrs.get("value"),
                    self.PREVIOUSPAGE_FIELD: tree.select(
                        "#{}".format(self.PREVIOUSPAGE_FIELD)
                    )[0].attrs.get("value"),
                }
                _LOGGER.debug(login_info)
                _LOGGER.info("Attempting login to Alarm.com")
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load login page from Alarm.com")
            return False
        except (AttributeError, IndexError):
            _LOGGER.error("Unable to extract login info from Alarm.com")
            raise
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
                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not login to Alarm.com")
            return False
        except KeyError:
            _LOGGER.error("Unable to extract ajax key from Alarm.com")
            raise
        return True

    async def _async_get_system_info(self):
        try:
            # grab system id
            async with self._websession.get(
                url=self.SYSTEMITEMS_URL, headers=self._ajax_headers
            ) as resp:
                json = await (resp.json())
            self._systemid = json["data"][0]["id"]
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load system data from Alarm.com")
            return False
        except (KeyError, IndexError):
            _LOGGER.error("Unable to extract system id from Alarm.com")
            raise
        try:
            # grab partition id
            async with self._websession.get(
                url=self.SYSTEM_URL_TEMPLATE.format(self._url_base, self._systemid),
                headers=self._ajax_headers,
            ) as resp:
                json = await (resp.json())
            self._partitionid = json["data"]["relationships"]["partitions"]["data"][0][
                "id"
            ]
            thermostats = (
                json["data"]["relationships"].get("thermostats", {}).get("data", [])
            )
            self._thermostat_detected = len(thermostats) > 0

            # CHECK IF GARAGE DOORS EXIST ON SYSTEM
            garage_doors = (
                json["data"]["relationships"].get("garageDoors", {}).get("data", [])
            )
            self._garage_door_detected = len(garage_doors) > 0
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load partition data from Alarm.com")
            return False
        except (KeyError, IndexError):
            _LOGGER.error("Unable to extract partition id from Alarm.com")
            raise
        return True

    async def async_login(self):
        """Login to Alarm.com."""
        _LOGGER.debug("Attempting to log in to Alarm.com")
        if not await self._async_get_ajax_key():
            return False
        return await self._async_get_system_info()

    async def async_update(self):
        """Fetch the latest state."""
        _LOGGER.debug("Calling update on Alarm.com")
        if not self._ajax_headers["ajaxrequestuniquekey"]:
            await self.async_login()
        try:
            # grab partition status
            async with self._websession.get(
                url=self.PARTITION_URL_TEMPLATE.format(
                    self._url_base, self._partitionid
                ),
                headers=self._ajax_headers,
            ) as resp:
                json = await (resp.json())
            self.sensor_status = json["data"]["attributes"]["needsClearIssuesPrompt"]
            self.sensor_status = (
                "System needs to be cleared" if self.sensor_status else "System OK"
            )
            self.state = json["data"]["attributes"]["state"]
            self.state = self.STATEMAP[self.state]
            _LOGGER.debug(
                "Got state %s, mapping to %s",
                json["data"]["attributes"]["state"],
                self.state,
            )
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load state data from Alarm.com")
            return False
        except KeyError:
            _LOGGER.error("Unable to extract state data from Alarm.com")
            # We may have timed out. Re-login again
            self.state = None
            self.sensor_status = None
            self._ajax_headers["ajaxrequestuniquekey"] = None
            await self.async_update()
        try:
            async with self._websession.get(
                url=self.SENSOR_STATUS_URL_TEMPLATE.format(self._url_base),
                headers=self._ajax_headers,
            ) as resp:
                json = await (resp.json())
            for sensor in json["data"]:
                self.sensor_status += (
                    ", "
                    + sensor["attributes"]["description"]
                    + " is "
                    + sensor["attributes"]["stateText"]
                )
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load sensor status from Alarm.com")
            return False
        except KeyError:
            _LOGGER.error("Unable to extract sensor status from Alarm.com")
            raise
        if self._thermostat_detected:
            try:
                async with self._websession.get(
                    url=self.THERMOSTAT_STATUS_URL_TEMPLATE.format(self._url_base),
                    headers=self._ajax_headers,
                ) as resp:
                    json = await (resp.json())
                for sensor in json["data"]:
                    for attribute in self.THERMOSTAT_ATTRIBUTES:
                        if attribute not in sensor["attributes"]:
                            continue
                        self.sensor_status += (
                            ", "
                            + sensor["attributes"]["description"]
                            + "_"
                            + attribute
                            + " is "
                            + str(sensor["attributes"][attribute])
                        )
            except (asyncio.TimeoutError, aiohttp.ClientError):
                _LOGGER.error("Can not load thermostat status from Alarm.com")
                return False
            except KeyError:
                _LOGGER.error("Unable to extract thermostat status from Alarm.com")
                raise

        # GET GARAGE DOOR STATUS
        if self._garage_door_detected:
            try:
                async with self._websession.get(
                    url=self.GARAGE_DOOR_STATUS_URL_TEMPLATE.format(self._url_base),
                    headers=self._ajax_headers,
                ) as resp:
                    json = await (resp.json())
                for sensor in json["data"]:
                    garage_state = sensor["attributes"]["state"]
                    garage_state = self.GARAGE_DOOR_STATEMAP[garage_state]
                    self.sensor_status += (
                        ", "
                        + sensor["attributes"]["description"]
                        + " is "
                        + garage_state
                    )
            except (asyncio.TimeoutError, aiohttp.ClientError):
                _LOGGER.error("Can not load garage door status from Alarm.com")
                return False
            except KeyError:
                _LOGGER.error("Unable to extract garage door status from Alarm.com")
                raise
        try:
            async with self._websession.get(
                url=self.TROUBLECONDITIONS_URL_TEMPLATE.format(self._url_base),
                headers=self._ajax_headers,
            ) as resp:
                json = await (resp.json())
            for troublecondition in json["data"]:
                self.sensor_status += (
                    ", " + troublecondition["attributes"]["description"]
                )
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load trouble conditions from Alarm.com")
            return False
        except KeyError:
            _LOGGER.error("Unable to extract trouble conditions from Alarm.com")
            raise
        return True

    async def _send(self, event, forcebypass, noentrydelay, silentarming):
        """Generic function for sending commands to Alarm.com

        :param event: Event command to send to alarm.com
        """
        _LOGGER.debug("Sending %s to Alarm.com", event)
        if event == "Disarm":
            json = {"statePollOnly": False}
        else:
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
        async with self._websession.post(
            url=self.PARTITION_URL_TEMPLATE.format(self._url_base, self._partitionid)
            + "/"
            + self.COMMAND_LIST[event]["command"],
            json=json,
            headers=self._ajax_headers,
        ) as resp:
            _LOGGER.debug("Response from Alarm.com %s", resp.status)
            if resp.status == 200:
                # Update alarm.com status after calling state change.
                await self.async_update()
            if resp.status == 403:
                # May have been logged out, try again
                _LOGGER.warning(
                    "Error executing %s, logging in and trying again...", event
                )
                await self.async_login()
                if event == "Disarm":
                    await self.async_alarm_disarm()
                elif event == "Arm+Stay":
                    await self.async_alarm_arm_stay()
                elif event == "Arm+Away":
                    await self.async_alarm_arm_away()
            elif resp.status >= 400:
                _LOGGER.error("%s failed with HTTP code %s", event, resp.status)
                _LOGGER.error(
                    "Arming parameters: force_bypass = %s, no_entry_delay = %s, silent_arming = %s",
                    forcebypass,
                    noentrydelay,
                    silentarming,
                )
        return True

    async def async_alarm_disarm(self):
        """Send disarm command."""
        await self._send("Disarm", False, False, False)

    async def async_alarm_arm_stay(self):
        """Send arm stay command."""
        forcebypass = self._forcebypass in ["stay", "true"]
        noentrydelay = self._noentrydelay in ["stay", "true"]
        silentarming = self._silentarming in ["stay", "true"]
        await self._send("Arm+Stay", forcebypass, noentrydelay, silentarming)

    async def async_alarm_arm_away(self):
        """Send arm away command."""
        forcebypass = self._forcebypass in ["away", "true"]
        noentrydelay = self._noentrydelay in ["away", "true"]
        silentarming = self._silentarming in ["away", "true"]
        await self._send("Arm+Away", forcebypass, noentrydelay, silentarming)


class AlarmdotcomADT(Alarmdotcom):
    """
    Access to control.adt.com portal.

    This class logs in via the control.adt.com portal instead of the alarm.com portal.
    """

    URL_BASE_ADT = "https://control.adt.com/"  # this overrides the URL_BASE in the Alarmdotcom class
    LOGIN_POST_URL_ADT = "https://control.adt.com/login.asp"  # this overrides the LOGIN_POST_URL in the Alarmdotcom class
    IDENTITY_URL_TEMPLATE = "{}system-install/api/identity"
    SKIP_2FA_URL_TEMPLATE = "{}system-install/api/engines/twoFactorAuthentication/twoFactorSettings/{}/skipTwoFactorSetup"
    DOTNETLOGIN_URL_TEMPLATE = (
        "{}system-install/api/installmanager/getCustomerDotNetLoginUrl"
    )
    WRAPUPJOURNEY_URL_TEMPLATE = "{}system-install/api/installmanager/wrapupJourney"

    async def _async_get_ajax_key_adt(self):
        try:
            # login and grab ajax key
            async with self._websession.post(
                url=self.LOGIN_POST_URL_ADT,
                data={
                    "JavaScriptTest": 1,
                    "cookieTest": 1,
                    "login": self._username,
                    "password": self._password,
                    "submit_banner_form": "Login",
                },
            ) as resp:
                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not login to Alarm.com")
            return False
        except KeyError:
            _LOGGER.error("Unable to extract ajax key from Alarm.com")
            raise
        return True

    async def _async_get_system_info_adt(self):
        try:
            # grab system id
            async with self._websession.get(
                url=self.IDENTITY_URL_TEMPLATE.format(self._url_base),
                headers=self._ajax_headers,
            ) as resp:
                json = await resp.json()
            adt_id = json["value"]["id"]
            self._systemid = json["value"]["customerId"]
            await self._websession.post(
                url=self.SKIP_2FA_URL_TEMPLATE.format(self._url_base, adt_id),
                headers=self._ajax_headers,
            )
            async with self._websession.post(
                url=self.DOTNETLOGIN_URL_TEMPLATE.format(self._url_base),
                headers=self._ajax_headers,
            ) as resp:
                json = await resp.json()
            dotnet_url = json["value"]["url"]
            await self._websession.post(
                url=self.WRAPUPJOURNEY_URL_TEMPLATE.format(self._url_base),
                headers=self._ajax_headers,
            )
            async with self._websession.get(url=dotnet_url) as resp:
                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value
            # grab partition id
            async with self._websession.get(
                url=self.SYSTEM_URL_TEMPLATE.format(self._url_base, self._systemid),
                headers=self._ajax_headers,
            ) as resp:
                json = await (resp.json())
            self._partitionid = json["data"]["relationships"]["partitions"]["data"][0][
                "id"
            ]
            thermostats = (
                json["data"]["relationships"].get("thermostats", {}).get("data", [])
            )
            self._thermostat_detected = len(thermostats) > 0
            # check if garage doors exist on system
            garage_doors = (
                json["data"]["relationships"].get("garageDoors", {}).get("data", [])
            )
            self._garage_door_detected = len(garage_doors) > 0
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Network error encountered during log in")
            return False
        except (KeyError, IndexError):
            _LOGGER.warning("ADT log in style unsuccessful")
            raise
        return True

    async def async_login(self):
        """Log in to ADT."""
        _LOGGER.debug("Attempting to log in to ADT")
        try:
            self._url_base = self.URL_BASE_ADT
            if not await self._async_get_ajax_key_adt():
                raise KeyError
            return await self._async_get_system_info_adt()
        except (KeyError, IndexError):
            _LOGGER.warning("Falling back to ADC log in style")
            try:
                self._url_base = self.URL_BASE
                if not await self._async_get_ajax_key():
                    return False
                return await self._async_get_system_info()
            except (KeyError, IndexError):
                _LOGGER.error("Unable to log in")
                return False


class AlarmdotcomProtection1(AlarmdotcomADT):
    """
    Access to alarm.com portal for Protection 1.

    This class uses the alarm.com portal but uses some ADT style endpoints.
    """

    async def async_login(self):
        """Log in to Protection 1."""
        _LOGGER.debug("Attempting to log in to Protection 1")
        await self._async_get_ajax_key()
        try:
            if not await self._async_get_system_info_adt():
                return False
        except (KeyError, IndexError):
            _LOGGER.warning("Falling back to ADC log in style")
            try:
                return await self._async_get_system_info()
            except (KeyError, IndexError):
                _LOGGER.error("Unable to log in")
                return False
