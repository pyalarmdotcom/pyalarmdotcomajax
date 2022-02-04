"""
pyalarmdotcomajax CLI.

Based on https://github.com/uvjustin/pyalarmdotcomajax/pull/16 by Kevin David (@kevin-david)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import aiohttp

import pyalarmdotcomajax
from pyalarmdotcomajax.errors import (
    AuthenticationFailed,
    DataFetchFailed,
    TwoFactorAuthEnabled,
)

from . import ADCController
from .const import ArmingOption
from .entities import (
    ADCGarageDoor,
    ADCLock,
    ADCPartition,
    ADCSensor,
    ADCSensorSubtype,
    ADCSystem,
)


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
            "show verbose output. -v returns server response for all devices except"
            " systems. -vv returns server response for all devices."
        ),
        action="count",
        default=0,
        required=False,
    )
    parser.add_argument(
        "-x",
        "--include-unsupported",
        help="when used with -v, returns data for cameras, lights, and thermostats.",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--skip-2fa-nag",
        help=(
            "skips alarm.com alert screen about upcoming two-factor authentication"
            " mandate."
        ),
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
        alarm = ADCController(
            username=args.get("username", ""),
            password=args.get("password", ""),
            websession=session,
            forcebypass=ArmingOption.NEVER,
            noentrydelay=ArmingOption.NEVER,
            silentarming=ArmingOption.NEVER,
            twofactorcookie=args.get("cookie"),
        )

        try:
            await alarm.async_login(skip_2fa_nag=bool(args.get("skip_2fa_nag")))
        except TwoFactorAuthEnabled:

            print(args.get("one_time_password"))

            code: str | None
            if not (code := args.get("one_time_password")):
                print("Two factor authentication is enabled for this user.")
                code = input("Enter One-Time Password: ")

            device_name_input: str | None = None
            remember_me: bool = False
            if not (device_name_input := args.get("device_name")):
                print("Request a two factor authentication cookie?")
                remember_me_input: str = input("(y)es/(n)o: ")
                yesses = ["Y", "y", "yes", "Yes", "YES"]
                # noes = ["N", "n", "no", "No", "NO"]
                remember_me = bool(remember_me_input in yesses)

            if code:
                device_name: str | None = None
                if device_name_input:
                    device_name = device_name_input
                elif remember_me:
                    device_name = "pyalarmdotcomajax"
                cookie = await alarm.submit_2fa(code=code, device_name=device_name)
                print(f"Got 2FA Cookie: {cookie}")
            else:
                print(
                    "Not enough information provided to make a decision regarding"
                    " two-factor authentication."
                )
                sys.exit()

        await alarm.async_update()

        if args.get("verbose", 0) == 1:
            await _async_machine_output(
                alarm=alarm,
                include_systems=False,
                include_unsupported=args.get("include_unsupported", False),
            )
        elif args.get("verbose", 0) > 1:
            await _async_machine_output(
                alarm=alarm,
                include_systems=True,
                include_unsupported=args.get("include_unsupported", False),
            )
        else:
            _human_readable_output(alarm)


async def _async_machine_output(
    alarm: ADCController,
    include_systems: bool = False,
    include_unsupported: bool = False,
) -> None:
    """Output raw server responses."""

    try:
        print(
            await alarm.async_get_raw_server_responses(
                include_systems, include_unsupported
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


def _human_readable_output(alarm: ADCController) -> None:
    """Output user-friendly list of devices and statuses."""
    print(f"\nProvider: {alarm.provider_name}")
    print(f"Logged in as: {alarm.user_email} ({alarm.user_id})")

    print("\n*** SYSTEMS ***\n")
    if len(alarm.systems) == 0:
        print("(none found)")
    else:
        for system in alarm.systems:
            _print_element_tearsheet(system)

    print("\n*** PARTITIONS ***\n")
    if len(alarm.partitions) == 0:
        print("(none found)")
    else:
        for partition in alarm.partitions:
            _print_element_tearsheet(partition)

    print("\n*** SENSORS ***\n")
    if len(alarm.sensors) == 0:
        print("(none found)")
    else:
        for sensor in alarm.sensors:
            _print_element_tearsheet(sensor)

    print("\n*** LOCKS ***\n")
    if len(alarm.locks) == 0:
        print("(none found)")
    else:
        for lock in alarm.locks:
            _print_element_tearsheet(lock)

    print("\n*** GARAGE DOORS ***\n")
    if len(alarm.garage_doors) == 0:
        print("(none found)")
    else:
        for garage_door in alarm.garage_doors:
            _print_element_tearsheet(garage_door)

    print("\n")


def _print_element_tearsheet(
    element: ADCGarageDoor | ADCLock | ADCPartition | ADCSensor | ADCSystem,
) -> None:
    if element.battery_critical:
        battery = "Critical"
    elif element.battery_low:
        battery = "Low"
    else:
        battery = "Normal"

    malfunction = "\n   ~~MALFUNCTIONING~~" if element.malfunction else ""

    subtype = (
        f"\n        Sensor Type: {element.device_subtype.name}"
        if isinstance(element.device_subtype, ADCSensorSubtype)
        else None
    )

    desired_str = (
        f"(Desired: {element.desired_state})" if isinstance(element, ADCSystem) else ""
    )

    print(
        f"""{element.name} ({element.id_}){malfunction}{subtype}
        State: {element.state} {desired_str}
        Battery: {battery}"""
    )


def main() -> None:
    """Run primary CLI function via asyncio. Main entrypoint for command line tool."""
    asyncio.run(cli())
