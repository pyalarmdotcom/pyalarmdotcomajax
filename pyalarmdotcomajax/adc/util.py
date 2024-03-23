"""Helpers for adc CLI."""

# ruff: noqa: T201 C901 UP007

import asyncio
import inspect
from collections.abc import Callable
from enum import Enum
from functools import partial, wraps
from typing import Any, Optional, TypeVar, get_type_hints

import aiohttp
import typer
from rich import print
from rich.panel import Panel
from rich.prompt import InvalidResponse, Prompt, PromptBase
from rich.table import Table

from pyalarmdotcomajax import AlarmBridge
from pyalarmdotcomajax.adc.params import (
    Param_CookieT,
    Param_DeviceNameT,
    Param_OtpMethodT,
    Param_OtpT,
    Param_PasswordT,
    Param_UsernameT,
)
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
    OtpRequired,
    UnexpectedResponse,
)
from pyalarmdotcomajax.models.auth import OtpType

F = TypeVar("F", bound=Callable[..., Any])  # Generic type variable for functions

#########
# TYPES #
#########


class OtpPrompt(PromptBase[OtpType]):
    """
    A prompt that returns an OTP type.

    Overloads the Rich PromptBase class.
    """

    response_type = OtpType
    validate_error_message = "[prompt.invalid]Please enter an available OTP type"

    def process_response(self, value: str) -> OtpType:
        """Convert choices to an OtpType."""
        value = value.strip().lower()

        try:
            return OtpType[value]
        except KeyError as err:
            raise InvalidResponse(self.validate_error_message) from err


class UTyper(typer.Typer):
    """
    Define a Typer subclass with async command support.

    https://github.com/tiangolo/typer/issues/88#issuecomment-1627386014
    """

    def universal(self, func: Callable, *args: Any, **kwargs: Any) -> Callable[[F], F]:
        """Wrap the command function to support async execution."""
        decorator = func(*args, **kwargs)

        def add_runner(f: F) -> F:
            """Wrap the function with an async runner if it's async."""

            @wraps(f)
            def runner(*args: Any, **kwargs: Any) -> Any:
                """Execute the async function using asyncio.run."""
                asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))

            if inspect.iscoroutinefunction(f):
                return decorator(runner)  # type: ignore
            return decorator(f)  # type: ignore

        return add_runner

    def command(self, *args: Any, **kwargs: Any) -> Callable[[F], F]:
        """Wrap the command function to support async execution."""

        return self.universal(super().command, *args, **kwargs)

    def callback(self, *args: Any, **kwargs: Any) -> Callable[[F], F]:
        """Wrap the command function to support async execution."""

        return self.universal(super().callback, *args, **kwargs)


###########
# HELPERS #
###########


async def async_handle_otp_workflow(
    alarm: AlarmBridge,
    enabled_2fa_methods: list[OtpType],
    otp: str | None = None,
    otpmethod: OtpType | None = None,
    device_name: str | None = None,
) -> None:
    """Handle two-factor authentication workflow."""

    #
    # Determine which OTP method to use
    #

    code: str | None
    selected_otpmethod: OtpType
    if otp or (otpmethod == OtpType.app):
        # If an OTP is provided directly in the CLI, it's from an OTP app.
        selected_otpmethod = OtpType.app
    else:
        print(
            "[bold]Two factor authentication is enabled for this account.",
        )

        # Get list of enabled OTP methods.
        if len(enabled_2fa_methods) == 1:
            # If only one OTP method is enabled, use it without prompting user.
            selected_otpmethod = enabled_2fa_methods[0]
            print(f"Using {selected_otpmethod.name} for One-Time Password.")
        elif cli_otpmethod := otpmethod:
            # If multiple OTP methods are enabled, but the user provided one via CLI, use it.
            selected_otpmethod = OtpType(cli_otpmethod)
            print(f"Using {selected_otpmethod.name} for One-Time Password.")
        elif not (
            selected_otpmethod := OtpPrompt.ask(
                "[magenta bold underline]Which OTP method would you like to use?[/magenta bold underline]",
                choices=[x.name for x in enabled_2fa_methods],
            )
        ):
            print("[bold red]Valid OTP method was not entered.")
            raise AuthenticationFailed

        #
        # Request OTP
        #

        if selected_otpmethod in (OtpType.email, OtpType.sms):
            # Ask Alarm.com to send OTP if selected method is EMAIL or SMS.
            print(f"[bold yellow]Requesting One-Time Password via {selected_otpmethod.name}...")
            await alarm.auth_controller.request_otp(selected_otpmethod)

    #
    # Prompt user for OTP
    #

    code = Prompt.ask("[magenta bold underline]Enter One-Time Password[/magenta bold underline]")

    await alarm.auth_controller.submit_otp(code=code, method=selected_otpmethod, device_name=device_name)


async def initialize_bridge(
    ctx: typer.Context,
    username: Param_UsernameT,
    password: Param_PasswordT,
    bridge: Optional[AlarmBridge] = None,
    otp_method: Param_OtpMethodT = None,
    cookie: Param_CookieT = None,
    otp: Param_OtpT = None,
    device_name: Param_DeviceNameT = None,
) -> AlarmBridge:
    """CLI for Alarm.com. View system status, monitor real-time notifications, and change device states."""

    # Enforce mutual exclusivity of MFA options.
    # Cookie parameter can be entered as "" if env vars are set for all 3 arguments, but we want to test OTP prompts.
    if (otp_method is not None) + (otp is not None) + (cookie not in [None, ""]) > 1:
        raise typer.BadParameter("Cannot use more than one MFA option at a time.")

    # Arguments can be pulled from environment variables. Show to user to reduce confusion.
    login_table = Table.grid(padding=(0, 2, 0, 0))
    login_table.add_column()
    login_table.add_column()
    login_table.add_row("[bold]User:[/bold]", username)
    login_table.add_row(
        "[bold]Password:[/bold]", "****" if password else "[grey58 italic](Not Provided)[/grey58 italic]"
    )
    login_table.add_row("[bold]MFA Cookie:[/bold]", cookie or "[grey58 italic](Not Provided)[/grey58 italic]")
    print(Panel.fit(login_table, title="[bold][yellow]Logging in as:", border_style="yellow", title_align="left"))

    #####################
    # INITIALIZE BRIDGE #
    #####################

    if bridge:
        bridge.auth_controller.set_credentials(username, password, cookie)
    else:
        bridge = AlarmBridge(username, password, cookie)

    # Typer calls bridge.close() when context is closed.
    ctx.call_on_close(partial(asyncio.get_event_loop().run_until_complete, bridge.close()))

    #
    # LOG IN
    #

    try:
        # Initialize the connector
        await bridge.initialize()

    except ConfigureTwoFactorAuthentication as err:
        print("[red]Unable to log in. Please set up two-factor authentication for this account.")
        raise typer.Exit(1) from err

    except (TimeoutError, aiohttp.ClientError, UnexpectedResponse, NotAuthorized) as err:
        print("[red]Could not connect to Alarm.com.")
        raise typer.Exit(1) from err

    except AuthenticationFailed as err:
        print("[red]Invalid credentials.")
        raise typer.Exit(1) from err

    #
    # HANDLE MFA
    #

    except OtpRequired as exc:
        try:
            await async_handle_otp_workflow(bridge, exc.enabled_2fa_methods, otp, otp_method, device_name)
        except AuthenticationFailed as err:
            print("[bold red]Invalid OTP.")
            raise typer.Exit(1) from err

    return bridge


def summarize_cli_actions(cls: Any, include_params: bool = False) -> dict[str, dict[str, Any]]:
    """
    Summarize CLI action methods within a class, including their descriptions.

    Optionally include a summary of each method's parameters if `include_params` is True.

    Args:
        cls: The class to inspect.
        include_params: If True, include a summary of each method's parameters.

    Returns:
        A dictionary with method names as keys and methods (and optionally parameter summaries) as values.

    """
    cli_actions_summary = {}
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and hasattr(attr, "__cli_actions__"):
            method_info = {"method": attr}
            if include_params:
                params_summary = summarize_method_params(attr)
                method_info["params"] = params_summary
            cli_actions_summary[attr_name] = method_info
    return cli_actions_summary


def summarize_method_params(method: Callable[..., Any]) -> list[dict[str, str | list[str] | list[type] | bool]]:
    """
    Summarize method parameters, excluding 'self' and 'return'. Handle unions and Enums properly.

    Args:
        method: The method to summarize.

    Returns:
        A list of dictionaries with parameter names and their types or enum member names.

    """
    params_summary: list[dict[str, str | list[str] | list[type] | bool]] = []
    type_hints = get_type_hints(method)
    for name, param_type in type_hints.items():
        if name in ["self", "return"]:
            continue  # Skip 'self' and 'return' members

        type_info: list[type]
        required_param: bool = True

        # Initialize type info with direct type name if available
        type_info = [getattr(param_type, "__name__", param_type)]

        # Initialize choices for Enum members
        # choices = []

        # Check and expand for Enum members
        if isinstance(param_type, type) and issubclass(param_type, Enum):
            type_info = [param_type]
            # choices = list(param_type.__members__)
        elif hasattr(param_type, "__args__"):  # Handle Union types
            type_info = []
            for arg in param_type.__args__:
                if arg is type(None):
                    required_param = False
                elif issubclass(arg, Enum):
                    # choices = list(arg.__members__)
                    type_info.append(getattr(arg, "__name__", arg))
                # elif isinstance(arg, type):
                else:
                    type_info.append(getattr(arg, "__name__", arg))

        params_summary.append(
            {
                "name": str(name),
                "types": type_info,
                # "choices": choices,
                "required": bool(required_param),
            }
        )

    return params_summary
