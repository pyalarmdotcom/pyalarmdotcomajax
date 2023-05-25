"""Basic example for logging in using time-based one-time password via pyalarmdotcomajax."""

import asyncio
import sys

import aiohttp
import os
from pyalarmdotcomajax.const import OtpType
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    UnexpectedResponse,
    OtpRequired,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
)

# Pulls usernane and password from environment variables. Replace with string below if you don't want to use env vars.
USERNAME = os.environ.get("ADC_USERNAME")
PASSWORD = os.environ.get("ADC_PASSWORD")


async def main() -> None:
    """Request Alarm.com sensor data."""

    if not (USERNAME and PASSWORD):
        sys.exit("Missing account credentials.")

    async with aiohttp.ClientSession() as session:
        #
        # CREATE ALARM CONTROLLER
        #

        alarm = AlarmController(username=USERNAME, password=PASSWORD, websession=session)

        #
        # LOG IN
        #

        print(f"Logging in as {USERNAME}")

        try:
            await alarm.async_login()

        except ConfigureTwoFactorAuthentication:
            sys.exit("Unable to log in. Please set up two-factor authentication for this account.")

        except (aiohttp.ClientError, asyncio.TimeoutError, UnexpectedResponse):
            sys.exit("Could not connect to Alarm.com.")

        except AuthenticationFailed:
            sys.exit("Invalid credentials.")

        except NotAuthorized:
            sys.exit("Permission error.")

        except OtpRequired as exc:
            print("Two factor authentication is enabled for this user.")
            await handle_otp_workflow(alarm, exc.enabled_2fa_methods)

        #
        # PULL DEVICE DATA FROM ALARM.COM
        #

        await alarm.async_update()

        for sensor in alarm.devices.sensors.values():
            print(f"Name: {sensor.name}, Sensor Type: {sensor.device_subtype}, State: {sensor.state}")


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


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
