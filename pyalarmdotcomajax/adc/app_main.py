"""adc core CLI functions."""

# ruff: noqa: T201 C901 UP007

# adc -d "$ADC_USERNAME" "$ADC_PASSWORD" "$ADC_COOKIE"
# adc "$ADC_USERNAME" "$ADC_PASSWORD" "$ADC_COOKIE" stream

# from __future__ import annotations

import asyncio
from functools import partial
from typing import Annotated, Optional

import typer
import uvloop
from rich import print
from rich.panel import Panel

from pyalarmdotcomajax.adc.app_action import action_app
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
from pyalarmdotcomajax.adc.util import UTyper, initialize_bridge
from pyalarmdotcomajax.controllers import EventType
from pyalarmdotcomajax.models.base import AdcResource
from pyalarmdotcomajax.util import resources_pretty, resources_raw, slug_to_title
from pyalarmdotcomajax.websocket.client import WebSocketState

#######
# APP #
#######

app = UTyper(
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
    help="Interact with your Alarm.com alarm system from the command line. Use '[yellow]adc COMMAND --help[/yellow]' for more command-specific instructions.",
)
app.add_typer(action_app, name="action", no_args_is_help=True)


############
# COMMANDS #
############


@app.command(short_help="Monitor alarm.com for real time updates.")
async def stream(
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
    """Monitor alarm.com for real time updates. Use 'adc stream --help' for more information."""

    bridge = await initialize_bridge(
        ctx,
        username,
        password,
        None,
        otp_method,
        cookie,
        otp,
        device_name,
    )

    print(Panel.fit("[yellow bold]EVENT MONITOR[/yellow bold]", border_style="yellow"))
    print("[bold](Press Ctrl+C to exit.)")

    async with bridge:
        bridge.subscribe(partial(event_printer, json))
        bridge.ws_controller.subscribe_connection(ws_state_printer)

        try:
            # Keep event loop alive until cancelled.
            while True:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            pass


@app.command()
async def get(
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
    include_unsupported: Annotated[
        Optional[bool],
        typer.Option(
            "--include-unsupported",
            "-x",
            help="return basic data for all known unsupported devices. always outputs in verbose format.",
            show_default=False,
        ),
    ] = False,
) -> None:
    """Get a snapshot of system and device states."""

    bridge = await initialize_bridge(
        ctx,
        username,
        password,
        None,
        otp_method,
        cookie,
        otp,
        device_name,
    )

    print(Panel.fit("[yellow bold]SYSTEM STATUS[/yellow bold]", border_style="yellow"))

    if include_unsupported:
        print(bridge.device_catalogs.included_raw_str)
    elif json:
        print(bridge.resources_raw)
    else:
        print(bridge.resources_pretty)


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


if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    app()
