"""
pyalarmdotcomajax CLI.

Based on https://github.com/uvjustin/pyalarmdotcomajax/pull/16 by Kevin David (@kevin-david)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import platform
import sys

import aiohttp
import pyalarmdotcomajax
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax import AuthResult
from pyalarmdotcomajax.devices import Camera
from pyalarmdotcomajax.devices import GarageDoor
from pyalarmdotcomajax.devices import ImageSensor
from pyalarmdotcomajax.devices import Light
from pyalarmdotcomajax.devices import Lock
from pyalarmdotcomajax.devices import Partition
from pyalarmdotcomajax.devices import Sensor
from pyalarmdotcomajax.devices import System
from pyalarmdotcomajax.errors import AuthenticationFailed
from pyalarmdotcomajax.errors import DataFetchFailed
from pyalarmdotcomajax.errors import NagScreen
from pyalarmdotcomajax.extensions import ConfigurationOption

CLI_CARD_BREAK = "--------"


async def cli() -> None:
    """Support command-line development and testing. Not used in normal library operation."""

    parser = argparse.ArgumentParser(
        prog="adc",
        description=(
            "Basic command line debug interface for Alarm.com via pyalarmdotcomajax."
            " Shows device states in various formats."
        ),
    )
    parser.add_argument("-u", "--username", help="alarm.com username", required=True)
    parser.add_argument("-p", "--password", help="alarm.com password", required=True)
    parser.add_argument(
        "-c",
        "--cookie",
        help=(
            "two-factor authentication cookie. cannot be used with --one-time-password!"
        ),
        required=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help=(
            "show verbose output. -vv returns base64 image data for image sensor"
            " images."
        ),
        action="count",
        default=0,
        required=False,
    )
    parser.add_argument(
        "-x",
        "--include-unsupported",
        help="when used with -v, returns data for all known unsupported devices.",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-o",
        "--one-time-password",
        help=(
            "provide otp code for accounts that have two-factor authentication enabled."
            " cannot be used with --cookie!"
        ),
        required=False,
    )
    parser.add_argument(
        "-n",
        "--device-name",
        help=(
            "registers a device with this name on alarm.com and requests the two-factor"
            " authentication cookie for this device."
        ),
        required=False,
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="show pyalarmdotcomajax's debug output.",
        action="count",
        default=0,
        required=False,
    )
    parser.add_argument(
        "-ver",
        "--version",
        action="version",
        version=f"%(prog)s {pyalarmdotcomajax.__version__}",
    )
    args = vars(parser.parse_args())

    print(f"Logging in as {args.get('username')}.")

    if args.get("cookie") is not None:
        print(f"Using 2FA cookie {args.get('cookie')}.")

    if args.get("debug", 0) > 0:
        logging.basicConfig(level=logging.DEBUG)

    async with aiohttp.ClientSession() as session:
        alarm = pyalarmdotcomajax.AlarmController(
            username=args.get("username", ""),
            password=args.get("password", ""),
            websession=session,
            twofactorcookie=args.get("cookie"),
        )

        generated_2fa_cookie = None

        try:
            login_result = await alarm.async_login()
        except NagScreen:
            print(
                "Unable to log in. Please set up two-factor authentication for this"
                " account."
            )
            sys.exit()

        if login_result == AuthResult.OTP_REQUIRED:

            code: str | None
            if not (code := args.get("one_time_password")):
                print("Two factor authentication is enabled for this user.")
                code = input("Enter One-Time Password: ")

            if code:
                generated_2fa_cookie = await alarm.async_submit_otp(
                    code=code, device_name=args.get("device_name")
                )
            else:
                print(
                    "Not enough information provided to make a decision regarding"
                    " two-factor authentication."
                )
                sys.exit()

        if login_result == AuthResult.ENABLE_TWO_FACTOR:
            print(
                "Unable to log in. Please set up two-factor authentication for this"
                " account."
            )
            sys.exit()

        await alarm.async_update()

        if args.get("verbose", 0) == 1:
            await _async_machine_output(
                alarm=alarm,
                include_image_sensor_b64=False,
                include_unsupported=args.get("include_unsupported", False),
            )
        elif args.get("verbose", 0) > 1:
            await _async_machine_output(
                alarm=alarm,
                include_image_sensor_b64=True,
                include_unsupported=args.get("include_unsupported", False),
            )
        else:
            _human_readable_output(alarm, generated_2fa_cookie)

        if generated_2fa_cookie:
            print(f"\n2FA Cookie: {generated_2fa_cookie}\n")


async def _async_machine_output(
    alarm: AlarmController,
    include_image_sensor_b64: bool = False,
    include_unsupported: bool = False,
) -> None:
    """Output raw server responses."""

    try:
        print(
            await alarm.async_get_raw_server_responses(
                include_image_sensor_b64=include_image_sensor_b64,
                include_unsupported=include_unsupported,
            )
        )
    except PermissionError:
        print("Permission error. Check that your credentials are correct.")
    except DataFetchFailed:
        print("Connection error.")
    except AuthenticationFailed:
        print(
            "Authentication error. Check that your two factor authentication cookie is"
            " correct."
        )


def _human_readable_output(
    alarm: AlarmController, generated_2fa_cookie: str | None = None
) -> None:
    """Output user-friendly list of devices and statuses."""
    print(f"\nProvider: {alarm.provider_name}")
    print(f"Logged in as: {alarm.user_email} ({alarm.user_id})")

    print("\n*** SYSTEMS ***\n")
    if len(alarm.systems) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for system in alarm.systems:
            _print_element_tearsheet(system)
            print(CLI_CARD_BREAK)

    print("\n*** PARTITIONS ***\n")
    if len(alarm.partitions) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for partition in alarm.partitions:
            _print_element_tearsheet(partition)
            print(CLI_CARD_BREAK)

    print("\n*** SENSORS ***\n")
    if len(alarm.sensors) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for sensor in alarm.sensors:
            _print_element_tearsheet(sensor)
            print(CLI_CARD_BREAK)

    print("\n*** LOCKS ***\n")
    if len(alarm.locks) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for lock in alarm.locks:
            _print_element_tearsheet(lock)
            print(CLI_CARD_BREAK)

    print("\n*** GARAGE DOORS ***\n")
    if len(alarm.garage_doors) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for garage_door in alarm.garage_doors:
            _print_element_tearsheet(garage_door)
            print(CLI_CARD_BREAK)

    print("\n*** IMAGE SENSORS ***\n")
    if len(alarm.image_sensors) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for image_sensor in alarm.image_sensors:
            _print_element_tearsheet(image_sensor)
            print(CLI_CARD_BREAK)

    print("\n*** LIGHTS ***\n")
    if len(alarm.lights) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for light in alarm.lights:
            _print_element_tearsheet(light)
            print(CLI_CARD_BREAK)

    print("\n")

    print("\n*** CAMERAS ***\n")
    if len(alarm.cameras) == 0:
        print("(none found)")
    else:
        print(CLI_CARD_BREAK)
        for camera in alarm.cameras:
            _print_element_tearsheet(camera)
            print(CLI_CARD_BREAK)

    print("\n")


def _print_element_tearsheet(
    element: GarageDoor
    | Lock
    | Partition
    | Sensor
    | System
    | Light
    | ImageSensor
    | Camera,
) -> None:

    if element.battery_critical:
        battery = "Critical"
    elif element.battery_low:
        battery = "Low"
    else:
        battery = "Normal"

    desired_str = (
        f" (Desired: {element.desired_state.name})"
        if isinstance(element, System) and element.desired_state
        else ""
    )

    print(f"{element.name} ({element.id_})")

    attribute_str = "ATTRIBUTES: "

    if isinstance(element.device_subtype, Sensor.Subtype):
        attribute_str += (
            f'[Type: {element.device_subtype.name.title().replace("_"," ")}] '
        )

    if element.state:
        attribute_str += f"[STATE: {element.state.name.title()}{desired_str}] "

    attribute_str += f"[BATTERY: {battery}] "

    if element.read_only:
        attribute_str += f"[READ ONLY: {element.read_only}] "

    if isinstance(element, Light):
        # Disabling. Boring stat.
        # attribute_str += f"[REPORTS STATE: {element.supports_state_tracking}] "

        if element.brightness:
            attribute_str += f"[BRIGHTNESS: {element.brightness}%] "

    print(attribute_str)

    settings_str = "SETTINGS: "

    if element.settings:
        config_option: ConfigurationOption
        for _, config_option in element.settings.items():

            settings_str += (
                f'{{{{ {config_option["name"]} [Type:'
                f' {config_option["option_type"].name.title()}] '
                f'[State: {config_option["current_value"]}] }}}} '
            )

    print(settings_str)

    if element.malfunction:
        print("\n~~MALFUNCTION~~\n")

    for condition in element.trouble_conditions:
        print(
            """~~TROUBLE~~"""
            f"""{condition["title"]} ({condition["message_id"]})"""
            f"""{condition["body"]}"""
        )


def main() -> None:
    """Run primary CLI function via asyncio. Main entrypoint for command line tool."""

    # Below is necessary to prevent asyncio "Event loop is closed" error in Windows.
    if platform.system() == "Windows" and hasattr(
        asyncio, "WindowsSelectorEventLoopPolicy"
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore

    asyncio.run(cli())
