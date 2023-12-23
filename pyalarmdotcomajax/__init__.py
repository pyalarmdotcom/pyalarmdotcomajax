from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
from collections.abc import AsyncIterator
from datetime import datetime
from types import TracebackType
from typing import Any

import aiohttp
from bs4 import BeautifulSoup
from pydantic import ValidationError

from pyalarmdotcomajax.const import IDENTITIES_URL_TEMPLATE, URL_BASE, OtpType
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
    OtpRequired,
    UnexpectedResponse,
)
from pyalarmdotcomajax.models.identity import IdentityData, IdentityResponse, TwoFactorAuthenticationResponse

__version__ = "0.0.1"

MAX_RETRIES = 25

ALL_DEVICES_URL_TEMPLATE = (  # Substitute with base url and system ID.
    "{}web/api/settings/manageDevices/deviceCatalogs/{}"
)
ALL_SYSTEMS_URL_TEMPLATE = "{}web/api/systems/availableSystemItems?searchString="
ALL_RECENT_IMAGES_TEMPLATE = "{}web/api/imageSensor/imageSensorImages/getRecentImages"

# LOGIN & SESSION: BEGIN
LOGIN_TWO_FACTOR_COOKIE_NAME = "twoFactorAuthenticationId"

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
LOGIN_2FA_REQUEST_OTP_SMS_URL_TEMPLATE = (
    "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaSms"
)
LOGIN_2FA_REQUEST_OTP_EMAIL_URL_TEMPLATE = (
    "{}web/api/engines/twoFactorAuthentication/twoFactorAuthentications/{}/sendTwoFactorAuthenticationCodeViaEmail"
)

VIEWSTATE_FIELD = "__VIEWSTATE"
VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

KEEP_ALIVE_DEFAULT_URL = "/web/KeepAlive.aspx"
KEEP_ALIVE_URL_PARAM_TEMPLATE = "?timestamp={}"
KEEP_ALIVE_RENEW_SESSION_URL_TEMPLATE = "{}web/api/identities/{}/reloadContext"
KEEP_ALIVE_SIGNAL_INTERVAL_S = 60
SESSION_REFRESH_DEFAULT_INTERVAL_MS = 780000  # 13 minutes. Sessions expire at 15.

SCENE_REFRESH_INTERVAL_M = 60


class AlarmConnector:
    """Base class for communicating with Alarm.com via API."""

    _user_profile: IdentityData
    _session_refresh_interval_ms: int | None
    _keep_alive_url: str | None
    _user_id: int
    _provider_name: str
    _user_email: str

    def __init__(
        self,
        username: str,
        password: str,
        mfa_token: str = "",
    ):
        """Manage access to Alarm.com API and builds devices."""

        self._websession: aiohttp.ClientSession | None = None

        self._username: str = username
        self._password: str = password
        self._mfa_token: str = mfa_token
        self._ajax_key: str | None = None

        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(f"{__package__}")

        self._last_session_refresh: datetime | None = None

    async def initialize(self) -> None:
        """Initialize the connection to the bridge and fetch all data."""
        # Initialize all HUE resource controllers
        # fetch complete full state once and distribute to controllers

        # await self.fetch_full_state()

        # start event listener

        # await self._events.initialize()

        # subscribe to reconnect event

        # self._events.subscribe(
        #     self._handle_connect_event, (EventType.RECONNECTED, EventType.DISCONNECTED)
        # )

    #
    # CONTEXT FUNCTIONS
    #

    async def __aenter__(self) -> "AlarmConnector":  # noqa: UP037
        """Return Context manager."""

        await self.initialize()
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
        self.logger.info("Connection to bridge closed.")

    #
    # REQUEST FUNCTIONS
    #

    @contextlib.asynccontextmanager
    async def create_request(
        self, method: str, url: str, use_auth: bool = True, **kwargs: Any
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        """Make a request to the Alarm.com API.

        Returns a generator with aiohttp ClientResponse.
        """
        if self._websession is None:
            self._websession = aiohttp.ClientSession()

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        if "cookies" not in kwargs:
            kwargs["cookies"] = {}

        kwargs["headers"].update(
            {
                "User-Agent": f"pyalarmdotcomajax/{__version__}",
                "Referrer": "https://www.alarm.com/web/system/home",
            }
        )

        if use_auth:
            if not self._ajax_key:
                raise NotAuthorized("Not logged in.")
            kwargs["headers"].update(
                {"ajaxrequestuniquekey": self._ajax_key, "Accept": "application/vnd.api+json"}
            )
            kwargs["cookies"].update({"twoFactorAuthenticationId": self._mfa_token})

        async with self._websession.request(method, url, **kwargs) as res:
            yield res

    async def request(self, method: str, url: str, allow_login_repair: bool = True, **kwargs: Any) -> dict:
        """Make request to the api and return response data."""

        try:
            async with self.create_request(method, url, raise_for_status=True, **kwargs) as resp:
                if self.logger.level <= logging.DEBUG:
                    try:
                        resp_dump = json.dumps(await resp.json()) if resp.content_length else ""
                    except json.JSONDecodeError:
                        resp_dump = await resp.text() if resp.content_length else ""
                    self.logger.debug(
                        f"\n==============================Server Response ({resp.status})==============================\n"
                        f"URL: {url}\n"
                        f"{resp_dump}"
                        f"\nURL: {url}"
                        "\n=================================================================================\n"
                    )

                json_rsp = None
                error_codes = []

                try:
                    json_rsp = await resp.json()
                except aiohttp.ContentTypeError as err:
                    raise UnexpectedResponse("Response was not JSON.") from err

                # Retrieve errors from errors dict object.
                if isinstance(json_rsp, dict) and json_rsp.get("errors"):
                    error_codes = [
                        code
                        for error in json_rsp.get("errors", [])
                        if isinstance(error, dict) and isinstance((code := error.get("code")), int)
                    ]

                # 406: Not Authorized For Ember, 423: Processing Error
                if all(x in error_codes for x in [403, 426]):
                    self.logger.info(
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
                        "Two factor authentication required.\nMethod: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                    )

                if error_codes == [] and isinstance(json_rsp, dict):
                    return dict(json_rsp)

                # 422: ValidationError, 500: ServerProcessingError, 503: ServiceUnavailable
                raise UnexpectedResponse(
                    f"Method: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                )
        except AuthenticationFailed as err:
            if err.can_autocorrect and allow_login_repair:
                self.logger.info("Attempting to repair session.")

                try:
                    await self.login()
                    return await self.request(method, url, allow_login_repair=False, **kwargs)
                except Exception as err:
                    raise AuthenticationFailed from err

            raise

    #
    # AUTHENTICATION FUNCTIONS
    #

    async def login(self) -> None:
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
        self.logger.debug("Attempting to log in to Alarm.com")

        #
        # Step 1: Get login page and cookies
        #

        try:
            # Load login page once and grab hidden fields and cookies
            async with self.create_request(method="get", url=LOGIN_URL, use_auth=False) as resp:
                text = await resp.text()
                self.logger.debug("Response status from Alarm.com: %s", resp.status)
                tree = BeautifulSoup(text, "html.parser")
                login_info = {
                    VIEWSTATE_FIELD: tree.select(f"#{VIEWSTATE_FIELD}")[0].attrs.get("value"),
                    VIEWSTATEGENERATOR_FIELD: tree.select(f"#{VIEWSTATEGENERATOR_FIELD}")[0].attrs.get("value"),
                    EVENTVALIDATION_FIELD: tree.select(f"#{EVENTVALIDATION_FIELD}")[0].attrs.get("value"),
                    PREVIOUSPAGE_FIELD: tree.select(f"#{PREVIOUSPAGE_FIELD}")[0].attrs.get("value"),
                }

        except (AttributeError, IndexError, aiohttp.ClientResponseError) as err:
            self.logger.exception("Failed to load login page or extract state data.")
            raise UnexpectedResponse from err

        #
        # Step 2: Log in and save anti-forgery key
        #

        try:
            # login and grab ajax key
            async with self.create_request(
                method="post",
                url=LOGIN_POST_URL,
                data={
                    "ctl00$ContentPlaceHolder1$loginform$txtUserName": self._username,
                    "txtPassword": self._password,
                    VIEWSTATE_FIELD: login_info[VIEWSTATE_FIELD],
                    VIEWSTATEGENERATOR_FIELD: login_info[VIEWSTATEGENERATOR_FIELD],
                    EVENTVALIDATION_FIELD: login_info[EVENTVALIDATION_FIELD],
                    PREVIOUSPAGE_FIELD: login_info[PREVIOUSPAGE_FIELD],
                    "__EVENTTARGET": None,
                    "__EVENTARGUMENT": None,
                    "__VIEWSTATEENCRYPTED": None,
                    "IsFromNewSite": "1",
                },
                use_auth=False,
                raise_for_status=True,
            ) as resp:
                if re.search("m=login_fail", str(resp.url)) is not None:
                    raise AuthenticationFailed("Invalid username and password.")

                # Update anti-forgery cookie.
                # AFG cookie is not always present in the response. This seems to depend on the specific Alarm.com vendor, so a missing AFG key should not cause a failure.
                # Ref: https://www.alarm.com/web/system/assets/addon-tree-output/@adc/ajax/services/adc-ajax.js

                with contextlib.suppress(KeyError):
                    self._ajax_key = resp.cookies["afg"].value

        except (aiohttp.ClientResponseError, KeyError) as err:
            self.logger.exception("Failed to get AJAX key from Alarm.com.")
            raise UnexpectedResponse from err

        self._last_session_refresh = datetime.now()

        self.logger.debug("Logged in to Alarm.com.")

        #
        # Step 3: Get user's profile.
        #
        # If there are multiple profiles, we'll use the first one.

        self.logger.debug("Getting user profile.")

        try:
            identity_raw_response = await self.request(
                method="get", url=IDENTITIES_URL_TEMPLATE.format(URL_BASE, ""), allow_login_repair=False
            )

            identity_response = IdentityResponse.model_validate(identity_raw_response)

            self._user_profile = identity_response.data[0]
            self._user_id = self._user_profile.id_
            self._provider_name = self._user_profile.attributes.logoName

            self._user_email = [
                inclusion.attributes.loginEmailAddress
                for inclusion in identity_response.included
                if inclusion.id_ == self._user_id and inclusion.type_ == "profile/profile"
            ].pop(0)

            if not self._user_email:
                raise UnexpectedResponse("Failed to get user's email address.")
        except ValidationError as err:
            self.logger.exception(f"{__name__} _async_get_identity_info: Failed to get user's identity info.")
            self.logger.debug(
                f"{__name__} _async_get_identity_info: Server Response:\n{json.dumps(identity_response, indent=4)}"
            )
            raise AuthenticationFailed from err

        # Determine whether we need to refresh sessions.
        self._session_refresh_interval_ms = (
            self._user_profile.applicationSessionProperties.inactivityWarningTimeoutMs
            if self._user_profile.applicationSessionProperties.shouldTimeout
            else None
        )

        self._keep_alive_url = (
            self._user_profile.applicationSessionProperties.keepAliveUrl
            if self._user_profile.applicationSessionProperties.enableKeepAlive
            else None
        )

        # Determines whether user uses celsius or fahrenheit. This is used for conversions within thermostats.
        self._use_celsius = self._user_profile.localizeTempUnitsToCelsius

        self.logger.debug("*** START IDENTITY INFO ***")
        self.logger.debug(f"Provider: {self._provider_name}")
        self.logger.debug(f"User: {self._user_id} {self._user_email}")
        self.logger.debug(f"Keep Alive Interval: {self._session_refresh_interval_ms}")
        self.logger.debug(f"Keep Alive URL: {self._keep_alive_url}")
        self.logger.debug("*** END IDENTITY INFO ***")

        #
        # Step 4: Determine whether OTP is required
        #

        mfa_requirements_response = TwoFactorAuthenticationResponse.model_validate(
            await self.request(
                method="get", url=IDENTITIES_URL_TEMPLATE.format(URL_BASE, ""), allow_login_repair=False
            )
        )

        if mfa_requirements_response.data.attributes.showSuggestedSetup is True:
            raise ConfigureTwoFactorAuthentication

        enabled_otp_types_bitmask = mfa_requirements_response.data.attributes.enabledTwoFactorTypes
        enabled_2fa_methods = [
            otp_type for otp_type in OtpType if bool(enabled_otp_types_bitmask & otp_type.value)
        ]

        if (
            (OtpType.disabled in enabled_2fa_methods)
            or mfa_requirements_response.data.attributes.isCurrentDeviceTrusted is True
            or not enabled_otp_types_bitmask
            or not enabled_2fa_methods
        ):
            # 2FA is disabled, we can skip 2FA altogether.
            return

        self.logger.info(f"Requires two-factor authentication. Enabled methods are {enabled_2fa_methods}")

        raise OtpRequired(enabled_2fa_methods)


async def main() -> None:
    """Run application."""

    # Get the credentials from environment variables
    username = str(os.environ.get("ADC_USERNAME"))
    password = str(os.environ.get("ADC_PASSWORD"))
    mfa_token = os.environ.get("ADC_2FA_TOKEN")

    # Create an instance of AlarmConnector
    connector = AlarmConnector(username, password)

    try:
        # Initialize the connector
        await connector.initialize()

        # Log in to alarm.com
        await connector.login()

        # Perform other tasks here

    finally:
        # Close the connector
        await connector.close()


# Start the asyncio task
asyncio.run(main())
