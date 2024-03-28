"""adc core CLI functions."""

# ruff: noqa: T201 C901 UP007

# from __future__ import annotations

import asyncio
import platform
from functools import partial
from typing import Annotated, Optional

import typer
from rich import print
from rich.console import Group
from rich.panel import Panel

from pyalarmdotcomajax import AlarmBridge
from pyalarmdotcomajax.adc.common import bridge, collect_params
from pyalarmdotcomajax.adc.util import (
    UTyper,
    summarize_cli_actions,
    with_paremeters,
)
from pyalarmdotcomajax.controllers import EventType
from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.util import resources_pretty, resources_raw, slug_to_title
from pyalarmdotcomajax.version import __version__
from pyalarmdotcomajax.websocket.client import WebSocketState

############
# MAIN APP #
############

app = UTyper(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        print(f"pyalarmdotcomajax version: {__version__}")
        raise typer.Exit()


@app.callback()
def adc_callback(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            help="Get installed pyalarmdotcom version.",
            callback=version_callback,
            is_eager=True,
            show_default=False,
        ),
    ] = False,
) -> None:
    """Interact with your Alarm.com alarm system from the command line."""

    pass


############
# COMMANDS #
############


@app.command(
    short_help="Monitor alarm.com for real time updates. Use '[bright_cyan]adc stream --help[/bright_cyan]' for details.",
    add_help_option=True,
)
@with_paremeters(collect_params)
async def stream(
    ctx: typer.Context,
) -> None:
    """Monitor alarm.com for real time updates. Command takes no options."""

    bridge: AlarmBridge = ctx.obj["bridge"]

    print("\n")

    print(
        Panel(
            "[black on yellow bold]EVENT MONITOR[/black on yellow bold]",
            border_style="black",
            style="black on yellow",
        )
    )
    print("\n[bold](Press Ctrl+C to exit.)\n\n")

    async with bridge:
        bridge.subscribe(partial(event_printer, ctx.params["json"]))
        bridge.ws_controller.subscribe_connection(ws_state_printer)

        try:
            # Keep event loop alive until cancelled.
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass


@app.command(
    add_help_option=True,
    short_help="Get a snapshot of system and device states. Use '[bright_cyan]adc get --help[/bright_cyan]' for details.",
)
@with_paremeters(collect_params)
async def get(
    ctx: typer.Context,
    include_unsupported: Annotated[
        Optional[bool],
        typer.Option(
            "--include-unsupported",
            "-x",
            help="Return basic data for all known unsupported devices. Always outputs in verbose format.",
            show_default=False,
        ),
    ] = False,
) -> None:
    """Get a snapshot of system and device states."""

    bridge: AlarmBridge = ctx.obj["bridge"]

    print("\n")

    print(
        Panel(
            "[black on yellow bold]GET SYSTEM STATUS[/black on yellow bold]",
            border_style="black",
            style="black on yellow",
        )
    )

    if include_unsupported:
        output = bridge.device_catalogs.included_raw_str
    elif ctx.params["json"]:
        output = bridge.resources_raw
    else:
        output = bridge.resources_pretty

    print(Group(output, ""))


###########
# HELPERS #
###########


# Callable[WebSocketState, Any]
def ws_state_printer(state: WebSocketState, next_attempt_s: int | None) -> None:
    """Print WebSocket state."""

    if state in [WebSocketState.RECONNECTED]:
        print("[green]Reconnected to Alarm.com...")
    elif state == WebSocketState.CONNECTING:
        print("[orange1]Connecting to Alarm.com...")
    elif state == WebSocketState.DISCONNECTED:
        print(f"[red]Disconnected from Alarm.com. Next reconnect attempt in {next_attempt_s} seconds.")
    elif state == WebSocketState.DEAD:
        print("[red]Streaming stopped. Connection to Alarm.com is dead.")
    elif state == WebSocketState.CONNECTED:
        print("[green]Connected to Alarm.com.")
        print("[yellow]Streaming real-time updates...")


# Callable[[WebSocketNotificationType, WebSocketState | BaseWSMessage], Any]
def event_printer(verbose: bool, event_type: EventType, resource_id: str, resource: AdcResource | None) -> None:
    """Print event."""

    if resource:
        title = f"Event Notification > {slug_to_title(event_type.name)} > {resource_id}"
        if verbose:
            print(resources_raw(title, [resource]))
        else:
            print(resources_pretty(title, [resource]))


##############
# ACTION APP #
##############

action_app = UTyper(
    no_args_is_help=True,
    add_completion=False,
    add_help_option=True,
    subcommand_metavar="DEVICE_TYPE",
    short_help="Perform an action on a device in your alarm system. Use '[bright_cyan]adc action --help[/bright_cyan]' for details.",  # Redundancy required to prevent cropping in Typer markdown output.
    help="Perform an action on a device in your alarm system.",
)


# Dynamically add device types and their @cli_action() methods from each AlarmBridge device controller.
for controller in bridge.resource_controllers:
    if len(summary := summarize_cli_actions(controller, include_params=False)):
        # Create device type command group
        # (e.g.: Thermostat)
        device_type_app = UTyper(
            help=f"Perform an action on a {slug_to_title(controller.resource_type.name).lower()}.",
            short_help=f"Perform an action on a {slug_to_title(controller.resource_type.name).lower()}. Use '[bright_cyan]adc {controller.resource_type.name.lower()} --help[/bright_cyan]' for details.",
            add_help_option=True,
            no_args_is_help=True,
        )

        # Create commands within device type command group
        # e.g.: Set State
        cmd_meta: dict
        cmd_name: str
        for cmd_name, cmd_meta in summary.items():
            device_command = device_type_app.command(
                name=f"{cmd_name}",
                add_help_option=True,
                no_args_is_help=True,
            )(with_paremeters(collect_params, show_success=True)(cmd_meta["method"]))

        # Register device type command as typer sub-app
        action_app.add_typer(
            device_type_app,
            name=controller.resource_type.name.lower(),
            rich_help_panel="Device Types",
        )

# Add action app to main app
app.add_typer(
    action_app,
    name="action",
)

if __name__ == "__main__":
    # Below is necessary to prevent asyncio "Event loop is closed" error in Windows.
    if platform.system() == "Windows" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app()
