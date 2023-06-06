"""pyalarmdotcomajax CLI.

Based on https://github.com/uvjustin/pyalarmdotcomajax/pull/16 by Kevin David (@kevin-david)
"""

# ruff: noqa: T201 C901

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import platform
import sys
from collections.abc import Sequence
from dataclasses import asdict
from enum import Enum
from typing import Any

import aiohttp
from termcolor import colored, cprint

import pyalarmdotcomajax
from pyalarmdotcomajax.const import OtpType
from pyalarmdotcomajax.devices.registry import AllDevices_t, AttributeRegistry

from . import AlarmController
from .devices import BaseDevice, DeviceType
from .devices.sensor import Sensor
from .exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    InvalidConfigurationOption,
    NotAuthorized,
    OtpRequired,
    UnexpectedResponse,
)
from .extensions import ConfigurationOption
from .helpers import ExtendedEnumMixin, slug_to_title
from .websockets.client import WebSocketState

CLI_CARD_BREAK = ""  # "--------"


async def cli() -> None:
    """Support CLI development and testing. Not used in normal library operation."""

    parser = argparse.ArgumentParser(
        prog="adc",
        description=(
            "basic command line debug interface for alarm.com via pyalarmdotcomajax. shows device states in"
            " various formats."
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
        help="show verbose output. -vv returns base64 image data for image sensor images.",
        action="count",
        default=0,
        required=False,
    )
    parser.add_argument("-u", "--username", dest="username", help="alarm.com username", required=True)
    parser.add_argument("-p", "--password", dest="password", help="alarm.com password", required=True)

    parser.add_argument(
        "--otp-method",
        help="preferred OTP method to use during login if multiple are enabled for user account. case sensitive.",
        type=OtpType,
        action=EnumAction,
        required=False,
    )

    parser.add_argument(
        "-n",
        "--device-name",
        help=(
            "registers a device with this name on alarm.com and requests the two-factor authentication cookie for"
            " the device."
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
        help="two-factor authentication cookie. cannot be used with --one-time-password!",
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
        help="return basic data for all known unsupported devices. always outputs in verbose format.",
        action="store_true",
        required=False,
    )

    #
    # Setting Subparser
    #

    set_subparser = subparsers.add_parser(
        "set",
        description="set device configuration option",
        help="set device configuration option. use '%(prog)s set --help' for parameters",
    )

    set_subparser.add_argument("-i", "--device-id", help="Numeric Alarm.com device identifier.", required=True)
    set_subparser.add_argument(
        "-s",
        "--setting-slug",
        help=(
            "Identifier for setting. Appears in parenthesis after setting name in %(prog)s human readable output."
        ),
    )
    set_subparser.add_argument(
        "-k",
        "--new-value",
        help="New value for setting.",
    )

    #
    # WebSocket / stream Subparser
    #

    get_subparser = subparsers.add_parser(
        "stream",
        description="monitor alarm.com for real time updates",
        help="monitor alarm.com for real time updates over WebSockets. hit Ctrl + C to exit.",
    )

    ##########
    # SET UP #
    ##########

    args = vars(parser.parse_args())

    if args.get("debug", 0) > 0:
        logging.basicConfig(level=logging.DEBUG)
    elif args.get("action") == "stream":
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    ##########
    # LOG IN #
    ##########

    cprint(f"Logging in as {args.get('username')}.", "grey", "on_yellow", attrs=["bold"])

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

        try:
            await alarm.async_login()
        except ConfigureTwoFactorAuthentication:
            cprint(
                "Unable to log in. Please set up two-factor authentication for this account.",
                "red",
            )
            sys.exit()

        except (aiohttp.ClientError, asyncio.TimeoutError, UnexpectedResponse, NotAuthorized):
            cprint("Could not connect to Alarm.com.", "red")
            sys.exit()

        except AuthenticationFailed:
            cprint("Invalid credentials.", "red")
            sys.exit()

        except OtpRequired as exc:
            await async_handle_otp_workflow(alarm, args, exc.enabled_2fa_methods)

        #######################
        # REFRESH DEVICE DATA #
        #######################

        await alarm.async_update()

        device_type_output: dict = {}

        ###################
        # GET DEVICE DATA #
        ###################

        if args.get("action") == "get":
            # Process MACHINE output

            device_type_output = {
                slug_to_title(device_type.name): (
                    json.dumps(filtered_list)
                    if (
                        filtered_list := [
                            device
                            for device in [
                                *alarm.raw_catalog.get("included", []),
                                alarm.raw_system.get("data"),
                            ]
                            if device.get("type")
                            == AttributeRegistry.get_relationship_id_from_devicetype(device_type)
                        ]
                    )
                    else "\n(none found)\n"
                )
                for device_type in DeviceType
                if (
                    device_type
                    in AttributeRegistry.supported_device_types  # pylint: disable=unsupported-membership-test
                    or args.get("include_unsupported", False)
                )
            }

            # TODO: Include Image Sensor Image Data

            # Get & Add Human Output

            if (args.get("verbose", 0)) == 0:
                device_type_output.update(_human_output(alarm))

            # Print Account Info

            print(f"\nProvider: {alarm.provider_name}")
            print(f"Logged in as: {alarm.user_email} ({alarm.user_id})")
            print("")

            # Print Devices By Type

            for device_type_name, device_type_body in sorted(device_type_output.items()):
                cprint(
                    f"====[ {device_type_name} ]====",
                    "grey",
                    "on_yellow",
                    attrs=["bold"],
                )
                print(device_type_body)
                print("")

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

            if not (device := alarm.devices.get(device_id)):
                cprint(f"Unable to find a device with ID {device_id}.", "red")
                sys.exit(0)

            try:
                config_option: ConfigurationOption = device.settings[setting_slug]
            except KeyError:
                cprint(
                    f"{device.name} ({device_id}) does not have the setting {setting_slug}.",
                    "red",
                )
                sys.exit(0)

            #
            # Convert user input into proper type
            #

            if (config_option_type := config_option.value_type) in [bool, str, int]:
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
                        (
                            f"Acceptable valures for {setting_slug} are:"
                            f" {', '.join([member_name.lower() for member_name in config_option_type.names()])}"
                        ),
                        "red",
                    )
                    sys.exit(0)

            else:
                cprint("Unexpected value type. This is a bug.")
                sys.exit(0)

            # Submit new value.
            try:
                await device.async_change_setting(slug=setting_slug, new_value=typed_new_value)
            except asyncio.TimeoutError:
                cprint("Timed out while connecting to Alarm.com.")
            except (
                aiohttp.ClientError,
                asyncio.exceptions.CancelledError,
            ):
                cprint("Failed to connect to Alarm.com.")
            except UnexpectedResponse:
                cprint("Couldn't find settings on device configuration page.")
            except InvalidConfigurationOption:
                cprint(f"Couldn't load pyalarmdotcomajax configuration extension for {setting_slug}.")
            except TypeError as err:
                cprint(str(err), "red")
                sys.exit(0)

            # Check success
            if issubclass(device.settings.get(setting_slug, {}).value_type, Enum):
                reported_value = str(device.settings.get(setting_slug, {}).current_value.name).upper()
            else:
                reported_value = device.settings.get(setting_slug, {}).get("current_value")

            if str(reported_value).upper() == str(new_value).upper():
                cprint(
                    f"{config_option.name} was successfully changed to {new_value} for {device.name}.",
                    "green",
                )
            else:
                cprint(
                    f"Error changing {config_option.name} for {device.name}.",
                    "red",
                )

        ############################
        # STREAM REAL TIME UPDATES #
        ############################

        if args.get("action") == "stream":
            cprint(
                "Streaming real-time updates...",
                "grey",
                "on_yellow",
                attrs=["bold"],
            )
            cprint(
                "(Press Ctrl+C to exit.)",
                attrs=["bold"],
            )

            await _async_stream_realtime(alarm)


#############
# FUNCTIONS #
#############


async def _async_stream_realtime(alarm: AlarmController) -> None:
    """Stream real-time updates via WebSockets."""

    # Keep user session alive.
    await alarm.start_session_nudger()

    def ws_state_handler(state: WebSocketState) -> None:
        """Handle websocket connection state changes."""

        if state in [WebSocketState.DISCONNECTED]:
            # asyncio.create_task(alarm.async_connect())
            cprint("Lost streaming connection to Alarm.com.", "red")
            sys.exit()

    alarm.start_websocket(ws_state_handler)

    try:
        # Keep event loop alive until cancelled.
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass

    finally:
        # Close connections & stop tasks when cancelled.

        await alarm.stop_session_nudger()

        alarm.stop_websocket()


def _human_output(alarm: AlarmController) -> dict:
    """Output user-friendly list of devices and statuses."""

    output = {}

    for device_type in AttributeRegistry.supported_device_types:  # pylint: ignore=not-an-iterable
        devices: dict[str, AllDevices_t] = getattr(alarm.devices, AttributeRegistry.get_storage_name(device_type))
        device_type_output: str = ""
        if len(devices) == 0:
            device_type_output += "\n(none found)\n"
        else:
            for device in sorted(devices.values(), key=lambda device: str(device.name)):
                device_type_output += _print_element_tearsheet(device)

        output[slug_to_title(device_type.name)] = device_type_output

    return output


def _print_element_tearsheet(
    element: AllDevices_t,
) -> str:
    output_str: str = ""

    # DEVICE NAME
    output_str += colored(f"\n{element.name} ({element.id_})", attrs=["bold", "underline"])

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

    # ATTRIBUTES
    output_str += "ATTRIBUTES: "

    if isinstance(element.device_subtype, Sensor.Subtype) or element.state or battery or element.read_only:
        if isinstance(element.device_subtype, Sensor.Subtype):
            output_str += f'[TYPE: {element.device_subtype.name.title().replace("_"," ")}] '

        if element.state:
            output_str += f"[STATE: {element.state.name.title()}] "

        if battery:
            output_str += f"[BATTERY: {battery}] "

        if element.read_only:
            output_str += f"[READ ONLY: {element.read_only}] "

        if hasattr(element, "brightness") and element.brightness:
            output_str += f"[BRIGHTNESS: {element.brightness}%] "

        # ENTITIES WITH "ATTRIBUTES" PROPERTY
        if isinstance(element.attributes, BaseDevice.DeviceAttributes):
            for name, value in asdict(element.attributes).items():
                output_str += f"[{str(name).upper()}: {value}] "
    else:
        output_str += "(none)"

        output_str += "\n"

    # SETTINGS / EXTENSIONS

    if element.settings:
        output_str += "SETTINGS: "

        config_option: ConfigurationOption
        for _, config_option in element.settings.items():
            if isinstance(current_value := config_option.current_value, Enum):
                current_value = current_value.name.title()

            output_str += (
                f"{{{{ {config_option.name} ({config_option.slug}) [Type:"
                f" {slug_to_title(config_option.option_type.name)}] "
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


async def async_handle_otp_workflow(
    alarm: AlarmController, args: dict[str, Any], enabled_2fa_methods: list[OtpType]
) -> None:
    """Handle two-factor authentication workflow."""

    #
    # Determine which OTP method to use
    #

    code: str | None
    selected_otp_method: OtpType
    if code := args.get("one_time_password"):
        # If an OTP is provided directly in the CLI, it's from an OTP app.
        selected_otp_method = OtpType.app
    else:
        cprint(
            "Two factor authentication is enabled for this user.",
            attrs=["bold"],
        )

        # Get list of enabled OTP methods.
        if len(enabled_2fa_methods) == 1:
            # If only one OTP method is enabled, use it without prompting user.
            selected_otp_method = enabled_2fa_methods[0]
            cprint(f"Using {selected_otp_method.name} for One-Time Password.")
        elif cli_otp_method := args.get("otp_method"):
            # If multiple OTP methods are enabled, but the user provided one via CLI, use it.
            selected_otp_method = OtpType(cli_otp_method)
            cprint(f"Using {selected_otp_method.name} for One-Time Password.")
        else:
            # If multiple OTP methods are enabled, let the user pick.
            cprint("\nAvailable one-time password methods:")
            for otp_method in enabled_2fa_methods:
                cprint(f"{otp_method.value}: {otp_method.name}")
            if not (
                selected_otp_method := OtpType(
                    int(input("\nWhich OTP method would you like to use? Enter the method's number: "))
                )
            ):
                cprint("Valid OTP method was not entered.", "red")
                sys.exit()

        #
        # Request OTP
        #

        if selected_otp_method in (OtpType.email, OtpType.sms):
            # Ask Alarm.com to send OTP if selected method is EMAIL or SMS.
            cprint(f"Requesting One-Time Password via {selected_otp_method.name}...")
            await alarm.async_request_otp(selected_otp_method)

    #
    # Prompt user for OTP
    #

    if not (code := input("Enter One-Time Password: ")):
        cprint("Requested OTP was not entered.", "red")
        sys.exit()

    await alarm.async_submit_otp(code=code, method=selected_otp_method)


class EnumAction(argparse.Action):
    """Argparse action for handling Enums.

    via https://stackoverflow.com/a/60750535 by Tim
    CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize action."""
        # Pop off the type value
        enum_type = kwargs.pop("type", None)

        # Ensure an Enum subclass is provided
        if enum_type is None:
            raise ValueError("type must be assigned an Enum when using EnumAction")
        if not issubclass(enum_type, Enum):
            raise TypeError("type must be an Enum when using EnumAction")

        # Generate choices from the Enum
        kwargs.setdefault("choices", tuple(e.name for e in enum_type if e != OtpType.disabled))

        super().__init__(**kwargs)

        self._enum = enum_type

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Convert value back into an Enum."""
        value = self._enum[values]
        setattr(namespace, self.dest, value)


def main() -> None:
    """Run primary CLI function via asyncio. Main entrypoint for command line tool."""

    # Below is necessary to prevent asyncio "Event loop is closed" error in Windows.
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(cli())
