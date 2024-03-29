"""Authentication management."""

from __future__ import annotations

import asyncio
import logging
import re
import socket
from typing import TYPE_CHECKING

import aiohttp
from bs4 import BeautifulSoup
from rich.console import Group

from pyalarmdotcomajax import const
from pyalarmdotcomajax.controllers.users import (
    IdentitiesController,
    ProfilesController,
)
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    OtpRequired,
    ServiceUnavailable,
    UnexpectedResponse,
)
from pyalarmdotcomajax.models.auth import (
    OtpType,
    TwoFactorAuthentication,
)
from pyalarmdotcomajax.models.jsonapi import Resource
from pyalarmdotcomajax.util import resources_pretty, resources_raw

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge

VIEWSTATE_FIELD = "__VIEWSTATE"
VIEWSTATEGENERATOR_FIELD = "__VIEWSTATEGENERATOR"
EVENTVALIDATION_FIELD = "__EVENTVALIDATION"
PREVIOUSPAGE_FIELD = "__PREVIOUSPAGE"

TWO_FACTOR_PATH = "engines/twoFactorAuthentication/twoFactorAuthentications"

log = logging.getLogger(__name__)

#
# API AVAILABLE SYSTEM RESPONSE
#


class AuthenticationController:
    """Controller for user identity."""

    def __init__(
        self,
        bridge: AlarmBridge,
        username: str | None = None,
        password: str | None = None,
        mfa_cookie: str | None = None,
    ) -> None:
        """Initialize authentication controller."""
        self._bridge = bridge

        # Credentials
        # We allow these to be set after initialization so that we can use an instantiated (but not initialized)
        # AlarmBridge to populate the adc cli command list.
        self._username: str = username or ""
        self._password: str = password or ""
        self.mfa_cookie: str = mfa_cookie or ""

        # Device Controllers
        self._identities = IdentitiesController(self._bridge)
        self._profiles = ProfilesController(self._bridge, self._identities)

    @property
    def resources_pretty(self) -> Group:
        """Return pretty Rich representation of resources in controller."""

        return resources_pretty("Users", [*self._identities.items, *self._profiles.items])

    @property
    def resources_raw(self) -> Group:
        """Return Rich representation raw JSON for all controller resources."""

        return resources_raw("Users", [*self._identities.items, *self._profiles.items])

    @property
    def included_raw_str(self) -> Group:
        """Return Rich representation of raw JSON for all controller resources."""

        return resources_raw("Users Children", [*self._identities.items, *self._profiles.items])

    @property
    def has_trouble_conditions_service(self) -> bool:
        """Whether the user has access to the trouble conditions service."""

        return self._identities.items[0].attributes.has_trouble_conditions_service

    @property
    def provider_name(self) -> str | None:
        """The name of the Alarm.com provider."""

        return self._identities.items[0].attributes.provider_name or None

    @property
    def session_refresh_interval_ms(self) -> int:
        """Interval at which session should be refreshed in milliseconds."""

        return (
            self._identities.items[0].attributes.application_session_properties.logout_timeout_ms or 5 * 60 * 1000
        )  # Default: 5 minutes

    @property
    def keep_alive_url(self) -> str | None:
        """URL for keep-alive requests, if keep alive is enabled."""

        return self._identities.items[0].attributes.application_session_properties.keep_alive_url

    @property
    def use_celsius(self) -> bool | None:
        """Whether the user uses celsius or fahrenheit."""

        return self._identities.items[0].attributes.localize_temp_units_to_celsius

    @property
    def profile_id(self) -> str:
        """The user's profile ID."""

        return self._profiles.items[0].id

    @property
    def enable_keep_alive(self) -> bool:
        """Whether keep-alive is enabled."""

        return (
            self._identities.items[0].attributes.application_session_properties.enable_keep_alive
            if self._identities.items[0].attributes.application_session_properties.enable_keep_alive is not None
            else True
        )

    def set_credentials(self, username: str, password: str, mfa_cookie: str | None = None) -> None:
        """Set the user's credentials."""

        self._username = username
        self._password = password
        self.mfa_cookie = mfa_cookie or ""

    async def login(self) -> None:
        """
        Log in to Alarm.com.

        Raises:
            OtpRequired: Username and password are correct. User now needs to begin two-factor authentication workflow.
            ConfigureTwoFactorAuthentication: Alarm.com requires that the user set up two-factor authentication for their account.
            UnexpectedResponse: Server returned status code >=400 or response object was not as expected.
            AuthenticationFailed: User could not be logged in, likely due to invalid credentials.

        """
        log.info("Logging in to Alarm.com")

        if "" in [self._username, self._password]:
            raise AuthenticationFailed("Username and password are required.")

        self._bridge.ajax_key = None

        #
        # Step 1: Get login page and cookies
        #

        login_info = await self._login_preload()

        #
        # Step 2: Log in and save first anti-forgery key
        #

        await self._login_submit_credentials(login_info)

        log.info("Logged in to Alarm.com.")

        #
        # Step 3: Determine whether OTP is required
        #

        log.info("Checking MFA requirements.")

        await self._login_otp_discovery()

    ###################
    # LOGIN FUNCTIONS #
    ###################

    async def _login_preload(self) -> dict[str, str]:
        """Step 1 of login process. Get login page and cookies."""

        retries = 0
        while True:
            try:
                # Load login page once and grab hidden fields and cookies
                async with self._bridge.create_request(
                    method="get",
                    accept_types=const.ResponseTypes.HTML,
                    use_ajax_key=False,
                    url=f"{const.URL_BASE}login",
                ) as resp:
                    resp.raise_for_status()

                    text = await resp.text()

                    tree = BeautifulSoup(text, "html.parser")
                    return {
                        VIEWSTATE_FIELD: tree.select(f"#{VIEWSTATE_FIELD}")[0].attrs.get("value"),
                        VIEWSTATEGENERATOR_FIELD: tree.select(f"#{VIEWSTATEGENERATOR_FIELD}")[0].attrs.get(
                            "value"
                        ),
                        EVENTVALIDATION_FIELD: tree.select(f"#{EVENTVALIDATION_FIELD}")[0].attrs.get("value"),
                        PREVIOUSPAGE_FIELD: tree.select(f"#{PREVIOUSPAGE_FIELD}")[0].attrs.get("value"),
                    }

            # Only retry for connection/server errors. No expectation of being logged in here, so we don't need to single out authentication errors.
            except (TimeoutError, aiohttp.ClientResponseError) as err:
                if retries == const.REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from err

                retries += 1
                continue

            except (AttributeError, IndexError, Exception) as err:
                raise UnexpectedResponse from err

    async def _login_submit_credentials(self, login_info: dict[str, str]) -> None:
        """Step 2 of login process. Submit credentials and get anti-forgery key."""

        retries = 0
        while True:
            try:
                # login and grab ajax key
                async with self._bridge.create_request(
                    method="post",
                    accept_types=const.ResponseTypes.FORM,
                    use_ajax_key=True,
                    url=f"{const.URL_BASE}web/Default.aspx",
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
                    raise_for_status=True,
                ) as resp:
                    if re.search("m=login_fail", str(resp.url)) is not None:
                        raise AuthenticationFailed
                    if re.search("m=LockedOut", str(resp.url)) is not None:
                        raise AuthenticationFailed("Account is locked.")
                    return

            except TimeoutError as err:
                if retries == const.REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from err
                retries += 1
                continue

            except (aiohttp.ClientResponseError, AttributeError, IndexError, Exception, KeyError) as err:
                raise AuthenticationFailed from err

    async def _login_otp_discovery(self) -> None:
        """Step 3 of login process. Determine whether OTP is required."""

        # User ID required to check OTP status
        await asyncio.gather(
            self._identities.initialize(),
            self._profiles.initialize(),
        )

        if not self._identities.items:
            raise UnexpectedResponse("No identities found.")

        response = await self._bridge.get(path=TWO_FACTOR_PATH, id=self._identities.items[0].id)

        if not isinstance(response.data, Resource):
            raise UnexpectedResponse

        mfa_details = TwoFactorAuthentication(response.data)

        if mfa_details.attributes.show_suggested_setup is True:
            raise ConfigureTwoFactorAuthentication

        enabled_otp_types_bitmask = mfa_details.attributes.enabled_two_factor_types
        enabled_2fa_methods = [
            otp_type for otp_type in OtpType if bool(enabled_otp_types_bitmask & otp_type.value)
        ]

        if (
            (OtpType.disabled in enabled_2fa_methods)
            or mfa_details.attributes.is_current_device_trusted is True
            or not enabled_otp_types_bitmask
            or not enabled_2fa_methods
        ):
            # 2FA is disabled, we can skip 2FA altogether.
            return

        log.info(f"Requires two-factor authentication. Enabled methods are {enabled_2fa_methods}")

        raise OtpRequired(
            enabled_2fa_methods,
            email=mfa_details.attributes.email,
            sms_country_code=mfa_details.attributes.sms_mobile_number.country
            if mfa_details.attributes.sms_mobile_number
            else None,
            sms_number=mfa_details.attributes.sms_mobile_number.mobile_number
            if mfa_details.attributes.sms_mobile_number
            else None,
        )

    #################
    # MFA FUNCTIONS #
    #################

    async def request_otp(self, method: OtpType | None) -> None:
        """Request e-mail or SMS OTP."""

        if method not in [OtpType.sms, OtpType.email]:
            return

        await self._bridge.post(
            path=TWO_FACTOR_PATH,
            id=self._identities.items[0].id,
            action="sendTwoFactorAuthenticationCodeViaSms"
            if method == OtpType.sms
            else "sendTwoFactorAuthenticationCodeViaEmail",
            mini_response=True,
        )

    async def submit_otp(self, code: str, method: OtpType, device_name: str | None = None) -> str | None:
        """Submit OTP and register device."""

        await self._bridge.post(
            path=TWO_FACTOR_PATH,
            id=self._identities.items[0].id,
            action="verifyTwoFactorCode",
            json={"code": code, "typeOf2FA": method.value},
            mini_response=True,
        )

        if not device_name:
            log.debug("Skipping device registration.")
            return None

        await self._bridge.post(
            path=TWO_FACTOR_PATH,
            id=self._identities.items[0].id,
            action="trustTwoFactorDevice",
            json={"deviceName": device_name if device_name else f"pyalarmdotcomajax on {socket.gethostname()}"},
            mini_response=True,
        )

        if not self.mfa_cookie:
            raise UnexpectedResponse("Could not find MFA cookie after submitting OTP and registering device.")

        return self.mfa_cookie
