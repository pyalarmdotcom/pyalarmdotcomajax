"""adc action command."""

import typer

from pyalarmdotcomajax import AlarmBridge
from pyalarmdotcomajax.adc.decorators import with_paremeters
from pyalarmdotcomajax.adc.params import (
    Param_CookieT,
    Param_DebugT,
    Param_DeviceNameT,
    Param_JsonT,
    Param_OtpMethodT,
    Param_OtpT,
    Param_PasswordT,
    Param_UsernameT,
    Param_VersionT,
)
from pyalarmdotcomajax.adc.util import UTyper, initialize_bridge, summarize_cli_actions
from pyalarmdotcomajax.util import slug_to_title

# ruff: noqa: T201 C901 UP007

action_app = UTyper(
    no_args_is_help=True,
    subcommand_metavar="DEVICE_TYPE",
    help="Perform an action on a device in your alarm system. Use '[yellow]adc action DEVICE_TYPE --help[/yellow]' for device-specific actions.",
    short_help="Perform an action on a device in your alarm system.",
)

bridge = AlarmBridge()


async def device_command_callback(
    ctx: typer.Context,
    username: Param_UsernameT,
    password: Param_PasswordT,
    otp_method: Param_OtpMethodT = None,
    cookie: Param_CookieT = None,
    json: Param_JsonT = False,
    otp: Param_OtpT = None,
    device_name: Param_DeviceNameT = None,
    debug: Param_DebugT = False,
    version: Param_VersionT = False,
) -> None:
    """Initialize bridge before running an action."""

    ctx.ensure_object(dict)

    print("Initializing Bridge")

    ctx.obj["bridge"] = await initialize_bridge(ctx, username, password, bridge, otp_method, cookie, otp)


for controller in bridge.resource_controllers:
    if len(summary := summarize_cli_actions(controller, include_params=False)):
        # Create device type command group
        # (e.g.: Thermostat)
        device_type_app = UTyper(
            help=f"Perform an action on a {slug_to_title(controller.resource_type.name).lower()}. Use 'adc action {controller.resource_type.name.lower()} COMMAND --help' for device-type parameters.",
            short_help=f"Perform an action on a {slug_to_title(controller.resource_type.name).lower()}.",
            no_args_is_help=True,
        )
        # device_type_app.callback()(device_command_callback)

        # Create commands within device type command group
        # e.g.: Set State
        cmd_meta: dict
        cmd_name: str
        for cmd_name, cmd_meta in summary.items():
            device_command = device_type_app.command(
                name=f"{cmd_name}",
            )(with_paremeters(device_command_callback)(cmd_meta["method"]))

        # Register device type command as typer sub-app
        action_app.add_typer(
            device_type_app, name=controller.resource_type.name.lower(), rich_help_panel="Device Types"
        )
