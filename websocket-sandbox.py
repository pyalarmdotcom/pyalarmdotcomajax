"""Basic example for logging in using time-based one-time password via pyalarmdotcomajax."""

import asyncio
import os
import sys

import aiohttp

from pyalarmdotcomajax import AlarmController, AuthResult
from pyalarmdotcomajax.errors import AuthenticationFailed, DataFetchFailed

USERNAME = os.environ.get("ADC_USERNAME")
PASSWORD = os.environ.get("ADC_PASSWORD")
TWOFA_COOKIE = os.environ.get("ADC_2FA_TOKEN")


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

        #
        # LOG IN AND HANDLE TWO-FACTOR AUTHENTICATION
        # OTP will be pushed to user automatically if OTP is set up via email or sms.
        #

        try:
            login_result = await alarm.async_login()

            if login_result == AuthResult.OTP_REQUIRED:
                print("Two factor authentication is enabled for this user.")

                if not (code := input("Enter One-Time Password: ")):
                    sys.exit("Requested OTP was not entered.")

                await alarm.async_submit_otp(code=code)

            elif login_result == AuthResult.ENABLE_TWO_FACTOR:
                sys.exit(
                    "Unable to log in. Please set up two-factor authentication for this"
                    " account."
                )

        except (ConnectionError, DataFetchFailed):
            sys.exit("Could not connect to Alarm.com.")

        except AuthenticationFailed:
            sys.exit("Invalid credentials.")

        #
        # PULL DEVICE DATA FROM ALARM.COM
        #

        # await alarm.async_update()

        ws_client = alarm.get_websocket_client()
        await ws_client.async_connect()


asyncio.run(main())
