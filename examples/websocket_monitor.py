"""Basic example for logging in using time-based one-time password via pyalarmdotcomajax."""

import asyncio
import logging
import os
import sys

import aiohttp

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.const import OtpType
from pyalarmdotcomajax.exceptions import ConfigureTwoFactorAuthentication, OtpRequired
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    UnexpectedResponse,
    NotAuthorized,
)
from pyalarmdotcomajax.websockets.client import WebSocketState

USERNAME = os.environ.get("ADC_USERNAME")
PASSWORD = os.environ.get("ADC_PASSWORD")
TWOFA_COOKIE = os.environ.get("ADC_2FA_TOKEN")

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


async def main() -> None:
    """Request Alarm.com sensor data."""

    if not (USERNAME and PASSWORD):
        sys.exit("Missing account credentials.")

    async with aiohttp.ClientSession() as session:
        #
        # CREATE ALARM CONTROLLER
        #

        alarm = AlarmController(
            username=USERNAME,
            password=PASSWORD,
            websession=session,
            twofactorcookie=TWOFA_COOKIE,
        )

        print(f"Logging in as {USERNAME}")

        try:
            await alarm.async_login()

        except ConfigureTwoFactorAuthentication:
            sys.exit("Unable to log in. Please set up two-factor authentication for this account.")

        except (aiohttp.ClientError, asyncio.TimeoutError, UnexpectedResponse, NotAuthorized):
            sys.exit("Could not connect to Alarm.com.")

        except AuthenticationFailed:
            sys.exit("Invalid credentials.")

        except OtpRequired as exc:
            print("Two factor authentication is enabled for this user.")
            await handle_otp_workflow(alarm, exc.enabled_2fa_methods)

        #
        # PULL DEVICE DATA FROM ALARM.COM
        #

        await alarm.async_update()

        #
        # OPEN WEBSOCKET CONNECTION
        #

        def ws_state_handler(state: WebSocketState) -> None:
            """Handle websocket connection state changes."""

            print(f"Websocket state changed to: {state.name}")

        alarm.start_websocket(ws_state_handler)

        try:
            # Keeps sessions alive and keeps event loop active.
            await alarm.start_session_nudger()

            # Keep event loop alive until cancelled.
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

        finally:
            # Close connection when cancelled.
            alarm.stop_websocket()

            await alarm.stop_session_nudger()


async def handle_otp_workflow(alarm: AlarmController, enabled_2fa_methods: list[OtpType]) -> None:
    """Handle two-factor authentication workflow."""

    selected_otp_method: OtpType

    #
    # Determine which OTP method to use
    #

    # Get list of enabled OTP methods.
    if len(enabled_2fa_methods) == 1:
        # If only one OTP method is enabled, use it without prompting user.
        selected_otp_method = enabled_2fa_methods[0]
        print(f"Using {selected_otp_method.name} for one-time password.")
    else:
        # If multiple OTP methods are enabled, let the user pick.
        print("\nAvailable one-time password methods:")
        for otp_method in enabled_2fa_methods:
            print(f"{otp_method.value}: {otp_method.name}")
        if not (
            selected_otp_method := OtpType(
                int(input("\nWhich OTP method would you like to use? Enter the method's number: "))
            )
        ):
            sys.exit("Valid OTP method was not entered.")

    #
    # Request OTP
    #

    if selected_otp_method in (OtpType.email, OtpType.sms):
        # Ask Alarm.com to send OTP if selected method is email or sms.
        print(f"Requesting One-Time Password via {selected_otp_method.name}...")
        await alarm.async_request_otp(selected_otp_method)

    #
    # Prompt user for OTP
    #

    if not (code := input("Enter One-Time Password: ")):
        sys.exit("Requested OTP was not entered.")

    await alarm.async_submit_otp(code=code, method=selected_otp_method)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
