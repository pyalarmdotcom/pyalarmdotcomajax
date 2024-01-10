"""Session, login, and user management."""

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
from mashumaro.exceptions import InvalidFieldValue, SuitableVariantNotFoundError

from pyalarmdotcomajax import const
from pyalarmdotcomajax.const import IDENTITIES_URL_TEMPLATE, URL_BASE, OtpType
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
    OtpRequired,
    ServiceUnavailable,
    UnexpectedResponse,
)
from pyalarmdotcomajax.models.jsonapi import FailureResponse, InfoResponse, JsonApiResponse, SuccessResponse
from pyalarmdotcomajax.models.session import (
    Identity,
    IdentityAttributes,
    Profile,
    ProfileAttributes,
    TwoFactorAuthentication,
)

__version__ = "0.0.1"


logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SessionController:
    """Base class for communicating with Alarm.com via API."""

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

        self._last_session_refresh: datetime | None = None

        # Initialize Empty Variables

        self._identity_attributes: IdentityAttributes | None = None
        self._profile_attributes: ProfileAttributes | None = None

        self._session_refresh_interval_ms: int | None = None
        self._keep_alive_url: str | None = None
        self._user_id: str | None = None
        self._provider_name: str | None = None
        self._user_email: str | None = None

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

    ##########################################
    # REQUEST MANAGEMENT / CONTEXT FUNCTIONS #
    ##########################################

    async def __aenter__(self) -> "SessionController":  # noqa: UP037
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
        log.info("Connection to bridge closed.")

    #
    # REQUEST FUNCTIONS
    #

    @contextlib.asynccontextmanager
    async def create_request(
        self,
        method: str,
        url: str,
        use_auth: bool = True,
        **kwargs: Any,
    ) -> AsyncIterator[aiohttp.ClientResponse]:
        """
        Make a request to the Alarm.com API.

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

    async def request(
        self,
        method: str,
        url: str,
        allow_login_repair: bool = True,
        **kwargs: Any,
    ) -> SuccessResponse:
        """Make request to the api and return response data."""

        try:
            async with self.create_request(method, url, raise_for_status=True, **kwargs) as resp:
                # If DEBUG logging is enabled, log the request and response.
                if log.level <= logging.DEBUG:
                    try:
                        resp_dump = json.dumps(await resp.json()) if resp.content_length else ""
                    except json.JSONDecodeError:
                        resp_dump = await resp.text() if resp.content_length else ""
                    log.debug(
                        f"\n==============================Server Response ({resp.status})==============================\n"
                        f"URL: {url}\n"
                        f"{resp_dump}"
                        f"\nURL: {url}"
                        "\n=================================================================================\n"
                    )

                # Load the response as JSON:API object.

                try:
                    jsonapi_response = JsonApiResponse.from_json(await resp.text())
                except SuitableVariantNotFoundError as err:
                    raise UnexpectedResponse("Response was not valid JSON:API format.") from err

                if isinstance(jsonapi_response, SuccessResponse):
                    return jsonapi_response

                if isinstance(jsonapi_response, InfoResponse):
                    raise UnexpectedResponse("Unhandled JSON:API info response.")

                if isinstance(jsonapi_response, FailureResponse):
                    # Retrieve errors from errors dict object.
                    error_codes = [int(error.code) for error in jsonapi_response.errors if error.code is not None]

                    # 406: Not Authorized For Ember, 423: Processing Error
                    if all(x in error_codes for x in [403, 426]):
                        log.info(
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

                # 422: ValidationError, 500: ServerProcessingError, 503: ServiceUnavailable
                raise UnexpectedResponse(
                    f"Method: {method}\nURL: {url}\nStatus Codes: {error_codes}\nRequest Body: {kwargs.get('data')}"
                )
        except AuthenticationFailed as err:
            if err.can_autocorrect and allow_login_repair:
                log.info("Attempting to repair session.")

                try:
                    await self.login()
                    return await self.request(method, url, allow_login_repair=False, **kwargs)
                except Exception as err:
                    raise AuthenticationFailed from err

            raise

    async def get(self, url: str, **kwargs: Any) -> SuccessResponse:
        """GET from server and mashumaro deserialized SuccessResponse."""
        return await self.request("get", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> SuccessResponse:
        """POST to server and mashumaro deserialized SuccessResponse."""
        return await self.request("post", url, **kwargs)

    ############################
    # AUTHENTICATION FUNCTIONS #
    ############################

    async def _login_get_login_info(self) -> dict[str, str]:
        """Step 1 of login process. Get login page and cookies."""

        retries = 0
        while True:
            try:
                # Load login page once and grab hidden fields and cookies
                async with self.create_request(method="get", url=const.LOGIN_URL, use_auth=False) as resp:
                    resp.raise_for_status()

                    text = await resp.text()

                    tree = BeautifulSoup(text, "html.parser")
                    return {
                        const.VIEWSTATE_FIELD: tree.select(f"#{const.VIEWSTATE_FIELD}")[0].attrs.get("value"),
                        const.VIEWSTATEGENERATOR_FIELD: tree.select(f"#{const.VIEWSTATEGENERATOR_FIELD}")[
                            0
                        ].attrs.get("value"),
                        const.EVENTVALIDATION_FIELD: tree.select(f"#{const.EVENTVALIDATION_FIELD}")[0].attrs.get(
                            "value"
                        ),
                        const.PREVIOUSPAGE_FIELD: tree.select(f"#{const.PREVIOUSPAGE_FIELD}")[0].attrs.get(
                            "value"
                        ),
                    }

            # Only retry for connection/server errors. No expectation of being logged in here, so we don't need to single out authentication errors.
            except (asyncio.TimeoutError, aiohttp.ClientResponseError) as err:
                if retries == const.REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from err

                retries += 1
                continue

            except (AttributeError, IndexError, Exception) as err:
                raise UnexpectedResponse from err

    async def _login_submit_credentials(self, login_info: dict[str, str]) -> str | None:
        """Step 2 of login process. Submit credentials and get anti-forgery key."""

        retries = 0
        while True:
            try:
                # login and grab ajax key
                async with self.create_request(
                    method="post",
                    url=const.LOGIN_POST_URL,
                    data={
                        "ctl00$ContentPlaceHolder1$loginform$txtUserName": self._username,
                        "txtPassword": self._password,
                        const.VIEWSTATE_FIELD: login_info[const.VIEWSTATE_FIELD],
                        const.VIEWSTATEGENERATOR_FIELD: login_info[const.VIEWSTATEGENERATOR_FIELD],
                        const.EVENTVALIDATION_FIELD: login_info[const.EVENTVALIDATION_FIELD],
                        const.PREVIOUSPAGE_FIELD: login_info[const.PREVIOUSPAGE_FIELD],
                        "__EVENTTARGET": None,
                        "__EVENTARGUMENT": None,
                        "__VIEWSTATEENCRYPTED": None,
                        "IsFromNewSite": "1",
                    },
                    use_auth=False,
                    raise_for_status=True,
                ) as resp:
                    if re.search("m=login_fail", str(resp.url)) is not None:
                        raise AuthenticationFailed

                    # Update anti-forgery cookie.
                    # AFG cookie is not always present in the response. This seems to depend on the specific Alarm.com vendor, so a missing AFG key should not cause a failure.
                    # Ref: https://www.alarm.com/web/system/assets/addon-tree-output/@adc/ajax/services/adc-ajax.js

                    return afg.value if (afg := resp.cookies.get("afg")) else None

            except KeyError as err:
                raise UnexpectedResponse from err

            except asyncio.TimeoutError as err:
                if retries == const.REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from err
                retries += 1
                continue

            except (aiohttp.ClientResponseError, AttributeError, IndexError, Exception) as err:
                raise UnexpectedResponse from err

    async def _login_get_identity(self) -> tuple[Identity, Profile]:
        """Step 3 of login process. Get user's identity and profile attributes."""

        identity: Identity | None = None
        profile: Profile | None = None

        retries = 0
        while True:
            try:
                identity_response = await self.get(
                    url=IDENTITIES_URL_TEMPLATE.format(URL_BASE, ""), allow_login_repair=False
                )
                break

            except (aiohttp.ClientResponseError, asyncio.TimeoutError) as e:
                if retries == const.REQUEST_RETRY_LIMIT:
                    raise ServiceUnavailable from e
                retries += 1
                continue

            except Exception as err:
                log.error("Failed to get user's identity info.")
                raise AuthenticationFailed from err

        # Extract user's identity
        if (
            isinstance(identity_response, SuccessResponse)
            and isinstance(identity_response.data, list)
            and isinstance(identity_response.data[0], Identity)
        ):
            identity = identity_response.data[0]
        else:
            raise UnexpectedResponse("Failed to get user's identity info.")

        # Extract user's profile
        if identity_response.included and isinstance(identity_response.included, list):
            for inclusion in identity_response.included:
                if isinstance(inclusion, Profile):
                    profile = inclusion
                    break

        if profile is None:
            raise UnexpectedResponse("Failed to get user's profile info.")

        return identity, profile

    async def _login_check_otp(self) -> None:
        """Step 4 of login process. Check whether OTP is required."""

        retries = 0
        while True:
            try:
                two_factor_response = await self.get(
                    url=IDENTITIES_URL_TEMPLATE.format(URL_BASE, ""), allow_login_repair=False
                )
                break

            except (aiohttp.ClientResponseError, asyncio.TimeoutError) as e:
                if retries == const.REQUEST_RETRY_LIMIT:
                    log.exception("[login > otp workflow] Max retries reached.")
                    raise ServiceUnavailable from e
                retries += 1
                continue
            except (InvalidFieldValue, Exception) as err:
                log.exception("[login > otp workflow]: Failed to start OTP workflow.")
                raise AuthenticationFailed from err

        if isinstance(two_factor_response.data, TwoFactorAuthentication) and (
            two_factor_attributes := two_factor_response.data.attributes
        ):
            if two_factor_attributes.show_suggested_setup is True:
                raise ConfigureTwoFactorAuthentication

            enabled_otp_types_bitmask = two_factor_attributes.enabled_two_factor_types
            enabled_2fa_methods = [
                otp_type for otp_type in OtpType if bool(enabled_otp_types_bitmask & otp_type.value)
            ]

            if (
                (OtpType.disabled in enabled_2fa_methods)
                or two_factor_attributes.is_current_device_trusted is True
                or not enabled_otp_types_bitmask
                or not enabled_2fa_methods
            ):
                # 2FA is disabled, we can skip 2FA altogether.
                return

            log.info(f"Requires two-factor authentication. Enabled methods are {enabled_2fa_methods}")

            raise OtpRequired(enabled_2fa_methods)

    async def login(self) -> None:
        """
        Log in to Alarm.com.

        Raises:
            OtpRequired: Username and password are correct. User now needs to begin two-factor authentication workflow.
            ConfigureTwoFactorAuthentication: Alarm.com requires that the user set up two-factor authentication for their account.
            UnexpectedResponse: Server returned status code >=400 or response object was not as expected.
            aiohttp.ClientError: Connection error.
            asyncio.TimeoutError: Connection error due to timeout.
            NotAuthorized: User doesn't have permission to perform the action requested.
            AuthenticationFailed: User could not be logged in, likely due to invalid credentials.
        """
        log.info("Logging in to Alarm.com")

        #
        # Step 1: Get login page and cookies
        #

        login_info = await self._login_get_login_info()

        #
        # Step 2: Log in and save anti-forgery key
        #

        self._ajax_key = await self._login_submit_credentials(login_info)
        self._last_session_refresh = datetime.now()

        log.info("Logged in to Alarm.com.")

        #
        # Step 3: Get user's profile.
        #
        # If there are multiple profiles, we'll use the first one.

        log.info("Getting user profile.")

        identity, profile = await self._login_get_identity()

        self._profile_attributes = profile.attributes
        self._identity_attributes = identity.attributes

        #
        # Break out useful identity/profile attributes.
        #

        self._user_id = profile.id_

        self._provider_name = self._identity_attributes.provider_name
        self._user_email = self._profile_attributes.email

        self._session_refresh_interval_ms = (
            self._identity_attributes.application_session_properties.logout_timeout_ms
            if self._identity_attributes.application_session_properties.should_timeout
            else None
        )

        self._keep_alive_url = (
            self._identity_attributes.application_session_properties.keep_alive_url
            if self._identity_attributes.application_session_properties.enable_keep_alive
            else None
        )

        # Determines whether user uses celsius or fahrenheit. This is used for conversions within thermostats.
        self._use_celsius = self._identity_attributes.localize_temp_units_to_celsius

        log.debug("*** START IDENTITY INFO ***")
        log.debug(f"Provider: {self._provider_name}")
        log.debug(f"User: {self._user_id} {self._user_email}")
        log.debug(f"Keep Alive Interval: {self._session_refresh_interval_ms}")
        log.debug(f"Keep Alive URL: {self._keep_alive_url}")
        log.debug("*** END IDENTITY INFO ***")

        #
        # Step 4: Determine whether OTP is required
        #

        log.info("Starting OTP workflow.")

        return await self._login_check_otp()


async def main() -> None:
    """Run application."""

    # Get the credentials from environment variables
    username = str(os.environ.get("ADC_USERNAME"))
    password = str(os.environ.get("ADC_PASSWORD"))
    mfa_token = str(os.environ.get("ADC_2FA_TOKEN"))

    # Create an instance of AlarmConnector
    connector = SessionController(username, password, mfa_token)

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
