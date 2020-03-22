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

    LOGIN_URL = "https://www.alarm.com/login"
    LOGIN_USERNAME_FIELD = "ctl00$ContentPlaceHolder1$loginform$txtUserName"
    LOGIN_PASSWORD_FIELD = "txtPassword"
    LOGIN_POST_URL = "https://www.alarm.com/web/Default.aspx"
    VIEWSTATE_FIELD = "__VIEWSTATE"
    VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
    EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
    PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"
    SYSTEMITEMS_URL = "https://www.alarm.com/web/api/systems/availableSystemItems"
    SYSTEM_URL_BASE = "https://www.alarm.com/web/api/systems/systems/"
    PARTITION_URL_BASE = "https://www.alarm.com/web/api/devices/partitions/"
    TROUBLECONDITIONS_URL = "https://www.alarm.com/web/api/troubleConditions/troubleConditions?forceRefresh=false"
    SENSOR_STATUS_URL = "https://www.alarm.com/web/api/devices/sensors"
    STATEMAP = (
        "",
        "disarmed",
        "armed stay",
        "armed away",
    )  # index is ADC's json status, value is integration's status
    COMMAND_LIST = {
        "Disarm": {"command": "disarm"},
        "Arm+Stay": {"command": "armStay"},
        "Arm+Away": {"command": "armAway"},
    }

    def __init__(
        self,
        username,
        password,
        websession,
        forcebypass=False,
        noentrydelay=False,
        silentarming=False,
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

    async def async_login(self):
        """Login to Alarm.com."""
        _LOGGER.debug("Attempting to log into Alarm.com...")
        try:
            # load login page once and grab VIEWSTATE/cookies
            async with self._websession.get(url=self.LOGIN_URL) as resp:
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
            ) as resp:
                self._ajax_headers["ajaxrequestuniquekey"] = resp.cookies["afg"].value
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not login to Alarm.com")
            return False
        except KeyError:
            _LOGGER.error("Unable to extract ajax key from Alarm.com")
            raise
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
                url=self.SYSTEM_URL_BASE + self._systemid, headers=self._ajax_headers
            ) as resp:
                json = await (resp.json())
            self._partitionid = json["data"]["relationships"]["partitions"]["data"][0][
                "id"
            ]
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not load partition data from Alarm.com")
            return False
        except (KeyError, IndexError):
            _LOGGER.error("Unable to extract partition id from Alarm.com")
            raise
        return True

    async def async_update(self):
        """Fetch the latest state."""
        _LOGGER.debug("Calling update on Alarm.com")
        if not self._ajax_headers["ajaxrequestuniquekey"]:
            await self.async_login()
        try:
            # grab partition status
            async with self._websession.get(
                url=self.PARTITION_URL_BASE + self._partitionid,
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
                url=self.SENSOR_STATUS_URL, headers=self._ajax_headers
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
        try:
            async with self._websession.get(
                url=self.TROUBLECONDITIONS_URL, headers=self._ajax_headers
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
                "forceBypass": forcebypass,
                "noEntryDelay": noentrydelay,
                "silentArming": silentarming,
                "statePollOnly": False,
            }
        try:
            async with self._websession.post(
                url=self.PARTITION_URL_BASE
                + self._partitionid
                + "/"
                + self.COMMAND_LIST[event]["command"],
                json=json,
                headers=self._ajax_headers,
            ) as resp:
                _LOGGER.debug("Response from Alarm.com %s", resp.status)
                if resp.status == 200:
                    # Update alarm.com status after calling state change.
                    await self.async_update()
                elif resp.status >= 400:
                    raise aiohttp.ClientError
        except aiohttp.ClientError:
            # May have been logged out, try again
            _LOGGER.error("Error executing %s, logging in and trying again...", event)
            await self.async_login()
            if event == "Disarm":
                await self.async_alarm_disarm()
            elif event == "Arm+Stay":
                await self.async_alarm_arm_stay()
            elif event == "Arm+Away":
                await self.async_alarm_arm_away()
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
