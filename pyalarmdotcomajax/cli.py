"""pyalarmdotcomajax CLI."""

# adc -u "$ADC_USERNAME" -p "$ADC_PASSWORD" -c "$ADC_COOKIE" get
# adc -u "$ADC_USERNAME" -p "$ADC_PASSWORD" -c "$ADC_COOKIE" stream

from __future__ import annotations

import argparse
import asyncio
import logging
import platform
import sys
from collections.abc import Sequence
from enum import Enum
from typing import Any

import aiohttp
from termcolor import cprint

from pyalarmdotcomajax import AlarmBridge, __version__
from pyalarmdotcomajax.controllers import EventType
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
    OtpRequired,
    UnexpectedResponse,
)
from pyalarmdotcomajax.models.auth import OtpType
from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.util import resources_pretty_str, resources_raw_str, slug_to_title

# ruff: noqa: T201 C901


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
        version=f"%(prog)s {__version__}",
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
        logging.basicConfig(level=5)
    # elif args.get("action") == "stream":
    #     logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    cprint(f"Logging in as {args.get('username')}.", "grey", "on_yellow", attrs=["bold"])

    if args.get("cookie") is not None:
        cprint(
            f"Using 2FA cookie {args.get('cookie')}.",
            "grey",
            "on_yellow",
            attrs=["bold"],
        )

    ##############
    # INITIALIZE #
    ##############

    bridge = AlarmBridge(args.get("username", ""), args.get("password", ""), args.get("cookie"))

    #
    # LOG IN
    #

    try:
        # Initialize the connector
        await bridge.initialize()

    except ConfigureTwoFactorAuthentication:
        cprint("Unable to log in. Please set up two-factor authentication for this account.", "red")
        sys.exit()

    except (TimeoutError, aiohttp.ClientError, UnexpectedResponse, NotAuthorized):
        cprint("Could not connect to Alarm.com.", "red")
        sys.exit()

    except AuthenticationFailed:
        cprint("Invalid credentials.", "red")
        sys.exit()

    #
    # HANDLE MFA
    #

    except OtpRequired as exc:
        await async_handle_otp_workflow(bridge, args, exc.enabled_2fa_methods)

    ###################
    # GET DEVICE DATA #
    ###################

    if args.get("action") == "get":
        if args.get("include_unsupported", False):
            print(bridge.device_catalogs.included_raw_str)
        elif (args.get("verbose", 0)) == 0:
            print(bridge.resources_pretty_str)
        else:
            print(bridge.resources_raw_str)

    ############################
    # STREAM REAL TIME UPDATES #
    ############################

    def event_printer_wrapper(event_type: EventType, resource_id: str, resource: AdcResource | None) -> None:
        """Call event printer with verbosity flag."""

        event_printer(
            verbose=args.get("verbose", 0) > 0, event_type=event_type, resource_id=resource_id, resource=resource
        )

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

        async with bridge:
            bridge.subscribe(event_printer_wrapper)

            try:
                # Keep event loop alive until cancelled.
                while True:
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                pass

    await bridge.close()


# Callable[[WebSocketNotificationType, WebSocketState | BaseWSMessage], Any]
def event_printer(verbose: bool, event_type: EventType, resource_id: str, resource: AdcResource | None) -> None:
    """Print event."""
    if resource:
        if verbose:
            print(
                resources_raw_str(
                    f"Event Notification: {slug_to_title(event_type.name)} {resource_id}", [resource]
                )
            )
        else:
            print(
                resources_pretty_str(
                    f"Event Notification: {slug_to_title(event_type.name)} {resource_id}", [resource]
                )
            )


class EnumAction(argparse.Action):
    """
    Argparse action for handling Enums.

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


async def async_handle_otp_workflow(
    alarm: AlarmBridge, args: dict[str, Any], enabled_2fa_methods: list[OtpType]
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
                raise AuthenticationFailed

        #
        # Request OTP
        #

        if selected_otp_method in (OtpType.email, OtpType.sms):
            # Ask Alarm.com to send OTP if selected method is EMAIL or SMS.
            cprint(f"Requesting One-Time Password via {selected_otp_method.name}...")
            await alarm.auth_controller.request_otp(selected_otp_method)

    #
    # Prompt user for OTP
    #

    if not (code := input("Enter One-Time Password: ")):
        cprint("Requested OTP was not entered.", "red")
        sys.exit()

    await alarm.auth_controller.submit_otp(code=code, method=selected_otp_method)


def main() -> None:
    """Run primary CLI function via asyncio. Main entrypoint for command line tool."""

    # Below is necessary to prevent asyncio "Event loop is closed" error in Windows.
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(cli())
