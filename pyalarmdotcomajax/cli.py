"""
pyalarmdotcomajax CLI.

Based on https://github.com/uvjustin/pyalarmdotcomajax/pull/16 by Kevin David (@kevin-david)
"""
from __future__ import annotations

import argparse
import asyncio
from enum import Enum
import logging
import platform
import sys
from typing import Any

import aiohttp
import pyalarmdotcomajax
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax import AuthResult
from pyalarmdotcomajax.devices import Camera
from pyalarmdotcomajax.devices import DEVICE_URLS
from pyalarmdotcomajax.devices import DeviceType
from pyalarmdotcomajax.devices import GarageDoor
from pyalarmdotcomajax.devices import ImageSensor
from pyalarmdotcomajax.devices import Light
from pyalarmdotcomajax.devices import Lock
from pyalarmdotcomajax.devices import Partition
from pyalarmdotcomajax.devices import Sensor
from pyalarmdotcomajax.devices import System
from pyalarmdotcomajax.errors import AuthenticationFailed
from pyalarmdotcomajax.errors import DataFetchFailed
from pyalarmdotcomajax.errors import InvalidConfigurationOption
from pyalarmdotcomajax.errors import NagScreen
from pyalarmdotcomajax.errors import UnexpectedDataStructure
from pyalarmdotcomajax.extensions import ConfigurationOption
from pyalarmdotcomajax.helpers import ExtendedEnumMixin
from pyalarmdotcomajax.helpers import slug_to_title
from termcolor import colored
from termcolor import cprint

CLI_CARD_BREAK = ""  # "--------"


async def cli() -> None:
    """Support command-line development and testing. Not used in normal library operation."""

    parser = argparse.ArgumentParser(
        prog="adc",
        description=(
            "basic command line debug interface for alarm.com via pyalarmdotcomajax."
            " shows device states in various formats."
        ),
    )

    ##################
    # BASE ARGUMENTS #
    ##################

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
        dest="version",
        action="version",
        version=f"%(prog)s {pyalarmdotcomajax.__version__}",
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
        "-u", "--username", dest="username", help="alarm.com username", required=True
    )
    parser.add_argument(
        "-p", "--password", dest="password", help="alarm.com password", required=True
    )

    parser.add_argument(
        "-n",
        "--device-name",
        help=(
            "registers a device with this name on alarm.com and requests the two-factor"
            " authentication cookie for the device."
        ),
        required=False,
    )

    ##########
    # GROUPS #
    ##########

    #
    # OTP/Cookie Group
    #

    otp_group = parser.add_mutually_exclusive_group()

    otp_group.add_argument(
        "-c",
        "--cookie",
        help=(
            "two-factor authentication cookie. cannot be used with --one-time-password!"
        ),
        required=False,
    )
    otp_group.add_argument(
        "-o",
        "--one-time-password",
        help=(
            "provide otp code for accounts that have two-factor authentication enabled."
            " if not provided here, %(prog)s will prompt user for otp. cannot be used"
            " with --cookie!"
        ),
        required=False,
    )

    ##############
    # SUBPARSERS #
    ##############

    subparsers = parser.add_subparsers(title="actions", required=True, dest="action")

    #
    # Fetch Subparser
    #

    get_subparser = subparsers.add_parser(
        "get",
        description="get data from alarm.com",
        help="get data from alarm.com. use '%(prog)s get --help' for parameters.",
    )

    get_subparser.add_argument(
        "-x",
        "--include-unsupported",
        help=(
            "return basic data for all known unsupported devices. always outputs in"
            " verbose format."
        ),
        action="store_true",
        required=False,
    )

    #
    # Setting Subparser
    #

    set_subparser = subparsers.add_parser(
        "set",
        description="set device configuration option",
        help=(
            "set device configuration option. use '%(prog)s set --help' for parameters"
        ),
    )

    set_subparser.add_argument(
        "-i", "--device-id", help="Numeric Alarm.com device identifier.", required=True
    )
    set_subparser.add_argument(
        "-s",
        "--setting-slug",
        help=(
            "Identifier for setting. Appears in parenthesis after setting name in"
            " %(prog)s human readable output."
        ),
    )
    set_subparser.add_argument(
        "-k",
        "--new-value",
        help="New value for setting.",
    )

    ##########
    # SET UP #
    ##########

    args = vars(parser.parse_args())

    if args.get("debug", 0) > 0:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    ##########
    # LOG IN #
    ##########

    cprint(
        f"Logging in as {args.get('username')}.", "grey", "on_yellow", attrs=["bold"]
    )

    if args.get("cookie") is not None:
        cprint(
            f"Using 2FA cookie {args.get('cookie')}.",
            "grey",
            "on_yellow",
            attrs=["bold"],
        )

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
            cprint(
                "Unable to log in. Please set up two-factor authentication for this"
                " account.",
                "red",
            )
            sys.exit()

        if login_result == AuthResult.OTP_REQUIRED:

            code: str | None
            if not (code := args.get("one_time_password")):
                cprint(
                    "Two factor authentication is enabled for this user.",
                    attrs=["bold"],
                )
                code = input("Enter One-Time Password: ")

            if code:
                generated_2fa_cookie = await alarm.async_submit_otp(
                    code=code, device_name=args.get("device_name")
                )
            else:
                cprint(
                    "Not enough information provided to make a decision regarding"
                    " two-factor authentication.",
                    "red",
                )
                sys.exit()

        if login_result == AuthResult.ENABLE_TWO_FACTOR:
            cprint(
                "Unable to log in. Please set up two-factor authentication for this"
                " account.",
                "red",
            )
            sys.exit()

        ######################
        # UPDATE DEVICE DATA #
        ######################

        await alarm.async_update()

        device_type_output: dict = {}

        ############################
        # GET DEVICE DATA WORKFLOW #
        ############################

        if args.get("action") == "get":

            # Built List of Device Types

            supported_device_types = []
            for device_type in DEVICE_URLS["supported"]:
                supported_device_types.append(device_type)

            unsupported_device_types = []
            if include_unsupported := args.get("include_unsupported", False):
                for device_type in DEVICE_URLS["unsupported"]:
                    unsupported_device_types.append(device_type)

            # Get & Add Machine Output

            if (verbose := args.get("verbose", 0)) > 0 or include_unsupported:
                device_type_output.update(
                    await _async_machine_output(
                        alarm=alarm,
                        include_image_sensor_b64=(verbose > 1),
                        device_types=supported_device_types + unsupported_device_types
                        if verbose > 0
                        else unsupported_device_types,
                    )
                )

            # Get & Add Human Output

            if verbose == 0:
                device_type_output.update(_human_output(alarm))

            # Print Account Info

            print(f"\nProvider: {alarm.provider_name}")
            print(f"Logged in as: {alarm.user_email} ({alarm.user_id})")
            print("")

            # Print Device Types

            for device_type_name, device_type_body in sorted(
                device_type_output.items()
            ):
                cprint(
                    f"====[ {device_type_name} ]====",
                    "grey",
                    "on_yellow",
                    attrs=["bold"],
                )
                print(device_type_body)
                print("")

            if generated_2fa_cookie:
                cprint(f"\n2FA Cookie: {generated_2fa_cookie}\n", "green")

        ############################
        # SET DEVICE DATA WORKFLOW #
        ############################

        if args.get("action") == "set":

            try:
                device_id: str = args["device_id"]
                setting_slug: str = args["setting_slug"]
                new_value: Any = args["new_value"]
            except AttributeError:
                cprint("Missing set parameter.", "red")

            if not (device := alarm.get_device_by_id(device_id)):
                cprint(f"Unable to find a device with ID {device_id}.", "red")
                sys.exit(0)

            try:
                config_option: ConfigurationOption = device.settings[setting_slug]
            except KeyError:
                cprint(
                    f"{device.name} ({device_id}) does not have the setting"
                    f" {setting_slug}.",
                    "red",
                )
                sys.exit(0)

            #
            # Convert user input into proper type
            #
            config_option_type = config_option["value_type"]

            if config_option_type in [bool, str, int]:
                try:
                    typed_new_value = config_option_type(new_value)
                except ValueError:
                    cprint(
                        f"Setting {setting_slug} must be {config_option_type.__name__}",
                        "red",
                    )
                    sys.exit(0)

            elif issubclass(config_option_type, ExtendedEnumMixin):
                try:
                    typed_new_value = config_option_type.enum_from_key(new_value)
                except ValueError:
                    cprint(
                        f"Acceptable valures for {setting_slug} are:"
                        f" {', '.join([member_name.lower() for member_name in config_option_type.names()])}",
                        "red",
                    )
                    sys.exit(0)

            else:
                cprint("Unexpected value type. This is a bug.")
                sys.exit(0)

            # Submit new value.
            try:
                await device.async_change_setting(
                    slug=setting_slug, new_value=typed_new_value
                )
            except asyncio.TimeoutError:
                cprint("Timed out while connecting to Alarm.com.")
            except (
                aiohttp.ClientError,
                asyncio.exceptions.CancelledError,
            ):
                cprint("Failed to connect to Alarm.com.")
            except UnexpectedDataStructure:
                cprint("Couldn't find settings on device configuration page.")
            except InvalidConfigurationOption:
                cprint(
                    "Couldn't load pyalarmdotcomajax configuration extension for"
                    f" {setting_slug}."
                )
            except TypeError as err:
                cprint(str(err), "red")
                sys.exit(0)

            # Check success
            if issubclass(
                device.settings.get(setting_slug, {}).get("value_type"), Enum
            ):
                reported_value = str(
                    device.settings.get(setting_slug, {}).get("current_value").name
                ).upper()
            else:
                reported_value = device.settings.get(setting_slug, {}).get(
                    "current_value"
                )

            if str(reported_value).upper() == str(new_value).upper():
                cprint(
                    f"{config_option.get('name')} was successfully changed to"
                    f" {new_value} for {device.name}.",
                    "green",
                )
            else:
                cprint(
                    f"Error changing {config_option.get('name')} for {device.name}.",
                    "red",
                )


#############
# FUNCTIONS #
#############


async def _async_machine_output(
    alarm: AlarmController,
    device_types: list,
    include_image_sensor_b64: bool = False,
) -> dict:
    """Output raw server responses."""

    try:
        responses = await alarm.async_get_raw_server_responses(
            include_image_sensor_b64=include_image_sensor_b64, device_types=device_types
        )
    except PermissionError:
        cprint("Permission error. Check that your credentials are correct.", "red")
    except DataFetchFailed:
        cprint("Connection error.", "red")
    except AuthenticationFailed:
        cprint(
            "Authentication error. Check that your two factor authentication cookie is"
            " correct.",
            "red",
        )

    return responses


def _human_output(alarm: AlarmController) -> dict:
    """Output user-friendly list of devices and statuses."""

    output = {}

    type_to_var: list[tuple[DeviceType, list]] = [
        (DeviceType.SYSTEM, alarm.systems),
        (DeviceType.PARTITION, alarm.partitions),
        (DeviceType.SENSOR, alarm.sensors),
        (DeviceType.LOCK, alarm.locks),
        (DeviceType.GARAGE_DOOR, alarm.garage_doors),
        (DeviceType.IMAGE_SENSOR, alarm.image_sensors),
        (DeviceType.LIGHT, alarm.lights),
        (DeviceType.CAMERA, alarm.cameras),
    ]

    device_type: DeviceType
    devices: list
    for device_type, devices in type_to_var:
        device_type_output: str = ""
        if len(devices) == 0:
            device_type_output += "\n(none found)\n"
        else:
            for device in sorted(devices, key=lambda device: str(device.name)):
                device_type_output += _print_element_tearsheet(device)

        output[slug_to_title(device_type.name)] = device_type_output

    return output


def _print_element_tearsheet(
    element: GarageDoor
    | Lock
    | Partition
    | Sensor
    | System
    | Light
    | ImageSensor
    | Camera,
) -> str:

    output_str: str = ""

    # DEVICE NAME
    output_str += colored(
        f"\n{element.name} ({element.id_})", attrs=["bold", "underline"]
    )

    if element.malfunction:
        output_str += colored(" (MALFUNCTION)", "red", attrs=["bold"])

    output_str += "\n"

    # BATTERY
    if element.battery_critical:
        battery = "Critical"
    elif element.battery_low:
        battery = "Low"
    else:
        battery = "Normal"

    # DESIRED STATE
    desired_str = (
        f" (Desired: {element.desired_state.name})"
        if isinstance(element, System) and element.desired_state
        else ""
    )

    # ATTRIBUTES
    output_str += "ATTRIBUTES: "

    if isinstance(element.device_subtype, Sensor.Subtype):
        output_str += f'[Type: {element.device_subtype.name.title().replace("_"," ")}] '

    if element.state:
        output_str += f"[STATE: {element.state.name.title()}{desired_str}] "

    output_str += f"[BATTERY: {battery}] "

    if element.read_only:
        output_str += f"[READ ONLY: {element.read_only}] "

    if isinstance(element, Light):
        # Disabling. Boring stat.
        # attribute_str += f"[REPORTS STATE: {element.supports_state_tracking}] "

        if element.brightness:
            output_str += f"[BRIGHTNESS: {element.brightness}%] "

    output_str += "\n"

    # SETTINGS / EXTENSIONS

    if element.settings:

        output_str += "SETTINGS: "

        config_option: ConfigurationOption
        for _, config_option in element.settings.items():

            if isinstance(current_value := config_option["current_value"], Enum):
                current_value = current_value.name.title()

            output_str += (
                f'{{{{ {config_option["name"]} ({config_option["slug"]}) [Type:'
                f' {slug_to_title(config_option["option_type"].name)}] '
                f"[State: {current_value}] }}}} "
            )

        output_str += "\n"

    # TROUBLE

    if element.trouble_conditions:
        for condition in element.trouble_conditions:
            output_str += colored("TROUBLE: ", "red", attrs=["bold"])
            output_str += f"""[TITLE: {condition["title"]}] [MESSAGE ID: {condition["message_id"]}] [MESSAGE: {condition["body"]}] """

        output_str += "\n"

    return output_str


def main() -> None:
    """Run primary CLI function via asyncio. Main entrypoint for command line tool."""

    # Below is necessary to prevent asyncio "Event loop is closed" error in Windows.
    if platform.system() == "Windows" and hasattr(
        asyncio, "WindowsSelectorEventLoopPolicy"
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore

    asyncio.run(cli())
