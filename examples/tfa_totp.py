"""Basic example for logging in using time-based one-time password via pyalarmdotcomajax."""

import asyncio
import sys

import aiohttp
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax import AuthResult
from pyalarmdotcomajax.errors import AuthenticationFailed
from pyalarmdotcomajax.errors import DataFetchFailed

USERNAME = "ENTER YOUR USERNAME"
PASSWORD = "ENTER YOUR PASSWORD"


async def main() -> None:
    """Request Alarm.com sensor data."""
    async with aiohttp.ClientSession() as session:

        #
        # CREATE ALARM CONTROLLER
        #

        alarm = AlarmController(
            username=USERNAME, password=PASSWORD, websession=session
        )

        #
        # LOG IN AND HANDLE TWO-FACTOR AUTHENTICATION
        # OTP will be pushed to user automatically if OTP is set up via email or sms.
        #

        try:

            login_result = await alarm.async_login()

            if login_result == AuthResult.OTP_REQUIRED:
                print("Two factor authentication is enabled for this user.")
                code = input("Enter One-Time Password: ")

                if not code:
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

        await alarm.async_update()

        for sensor in alarm.sensors:
            print(
                f"Name: {sensor.name}, Sensor Type: {sensor.device_subtype}, State:"
                f" {sensor.state}"
            )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
