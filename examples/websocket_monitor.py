"""Basic example for logging in using time-based one-time password via pyalarmdotcomajax."""

import asyncio
import logging
import os
import sys

import aiohttp

from pyalarmdotcomajax import AlarmController, OtpType
from pyalarmdotcomajax.errors import TwoFactor_ConfigurationRequired, TwoFactor_OtpRequired
from pyalarmdotcomajax.errors import AuthenticationFailed, DataFetchFailed
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

        try:
            await alarm.async_login()

        except TwoFactor_OtpRequired:
            print("Two factor authentication is enabled for this user.")
            await handle_otp_workflow(alarm)

        except TwoFactor_ConfigurationRequired:
            sys.exit("Unable to log in. Please set up two-factor authentication for this account.")

        except (ConnectionError, DataFetchFailed):
            sys.exit("Could not connect to Alarm.com.")

        except AuthenticationFailed:
            sys.exit("Invalid credentials.")

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
            # Keep event loop alive until cancelled.
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass

        finally:
            # Close connection when cancelled.
            alarm.stop_websocket()


async def handle_otp_workflow(alarm: AlarmController) -> None:
    """Handle two-factor authentication workflow."""

    selected_otp_method: OtpType

    #
    # Determine which OTP method to use
    #

    # Get list of enabled OTP methods.
    if len(enabled_2fa_methods := await alarm.async_get_enabled_2fa_methods()) == 1:
        # If only one OTP method is enabled, use it without prompting user.
        selected_otp_method = enabled_2fa_methods[0]
        print(f"Using {selected_otp_method.value} for One-Time Password.")
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

    if selected_otp_method in (OtpType.EMAIL, OtpType.SMS):
        # Ask Alarm.com to send OTP if selected method is EMAIL or SMS.
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
