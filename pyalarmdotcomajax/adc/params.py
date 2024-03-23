"""Common options for adc cli commands."""

import logging
from typing import TYPE_CHECKING, Annotated, Any, Optional

import click
import typer

from pyalarmdotcomajax.models.auth import OtpType
from pyalarmdotcomajax.version import __version__

if TYPE_CHECKING:
    from click.core import Context, Parameter

# ruff: noqa: T201 C901 UP007

# RICH OUTPUT PANELS
MAIN_MFA = "Multi-factor Authentication Options"
MAIN_OUTPUT = "Output Flags"
CREDENTIALS = "User Credentials"


class OtpParamType(click.Choice):
    """
    click.ParamType for OTP types.

    This class is necessary because we want users to interact with OTP types using the
    OtpType enum name instead of the OtpType enum value, which is Typer's default.
    """

    name = "OtpParamType"

    def __init__(self) -> None:
        """Initialize the OtpParamType class."""

        super().__init__(choices=[x.name for x in OtpType if x.name != "disabled"], case_sensitive=False)

    def convert(
        self,
        value: Any,
        param: Optional["Parameter"],
        ctx: Optional["Context"],
    ) -> int:
        """
        Convert the value to an OtpType.

        Outputs as int to as Typer expects enum parameters to be returned from prompt as enum value.
        """

        try:
            return OtpType[value].value
        except ValueError:
            self.fail(f"{value!r} is not a valid OTP type", param, ctx)


def version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        print(f"pyalarmdotcomajax version: {__version__}")
        raise typer.Exit()


def debug_callback(value: bool) -> None:
    """Set log level based on whether user requested debugging."""
    logging.basicConfig()
    if value:
        print("Debugging enabled.")
        logging.getLogger("pyalarmdotcomajax").setLevel(5)
    else:
        logging.getLogger("pyalarmdotcomajax").setLevel(logging.ERROR)


###################
# CORE PARAMETERS #
###################

Param_UsernameT = Annotated[
    str,
    typer.Argument(
        help="Alarm.com username", rich_help_panel=CREDENTIALS, show_default=False, envvar="ADC_USERNAME"
    ),
]
Param_PasswordT = Annotated[
    str,
    typer.Argument(
        help="Alarm.com password", rich_help_panel=CREDENTIALS, show_default=False, envvar="ADC_PASSWORD"
    ),
]
Param_CookieT = Annotated[
    Optional[str],
    typer.Argument(
        help="Two-factor authentication cookie. (Cannot be used with --one-time-password!)",
        show_default=False,
        rich_help_panel=CREDENTIALS,
        envvar="ADC_COOKIE",
    ),
]

#
# OPTIONS
#

Param_JsonT = Annotated[
    bool,
    typer.Option(
        "--json",
        "-j",
        help="Return JSON output from device endpoints instead of formatted output.",
        rich_help_panel=MAIN_OUTPUT,
        show_default=False,
    ),
]

#
# MFA OPTIONS
#

Param_OtpT = Annotated[
    Optional[str],
    typer.Option(
        "--otp",
        "-o",
        help="Provide app-based OTP for accounts that have two-factor authentication enabled. If not provided here, adc will prompt you for OTP. Cannot be used with --cookie or --otp-method!",
        show_default=False,
        rich_help_panel=MAIN_MFA,
    ),
]

Param_OtpMethodT = Annotated[
    Optional[OtpType],
    typer.Option(
        "--otp-method",
        "-m",
        help='OTP delivery method to use. Cannot be used alongside "cookie" argument. Defaults to "app" if --otp is provided, otherwise prompts for otp.',
        case_sensitive=False,
        show_choices=True,
        show_default=False,
        rich_help_panel=MAIN_MFA,
        click_type=OtpParamType(),
    ),
]

Param_DeviceNameT = Annotated[
    Optional[str],
    typer.Option(
        "--device-name",
        "-n",
        help="Registers a device with this name on alarm.com and requests the two-factor authentication cookie for the device.",
        rich_help_panel=MAIN_MFA,
        show_default=False,
    ),
]

#
# OUTPUT OPTIONS
#

Param_DebugT = Annotated[
    bool,
    typer.Option(
        "--debug",
        "-d",
        callback=debug_callback,
        help="Enable pyalarndotcomajax's debug logging.",
        rich_help_panel=MAIN_OUTPUT,
        is_eager=True,
        show_default=False,
    ),
]

Param_VersionT = Annotated[
    Optional[bool],
    typer.Option(
        "--version",
        help="Get installed pyalarmdotcom version.",
        callback=version_callback,
        is_eager=True,
        show_default=False,
    ),
]


#####################
# DEVICE PARAMETERS #
#####################
Param_Id = Annotated[
    str,
    typer.Argument(
        metavar="DEVICE_ID",
        help="A device's ID.",
        show_default=False,
    ),
]
