"""
pyalarmdotcomajax CLI.

Based on https://github.com/uvjustin/pyalarmdotcomajax/pull/16 by Kevin David (@kevin-david)
"""

import argparse
import asyncio
import logging

import aiohttp

import pyalarmdotcomajax
from pyalarmdotcomajax import ADCController
from pyalarmdotcomajax.entities import ADCBaseElement


async def main():
    """Support command-line development and testing. Not used in normal library operation."""

    parser = argparse.ArgumentParser(
        prog="pyalarmdotcomajax",
        description="Basic command line interface for Alarm.com",
    )
    parser.add_argument("-u", "--username", help="alarm.com username", required=True)
    parser.add_argument("-p", "--password", help="alarm.com password", required=True)
    parser.add_argument(
        "-c", "--cookie", help="two-factor authentication cookie", required=False
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="show debug output",
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

    print(f"Provider is {args.get('provider')}")

    print(f"Logging in as {args.get('username')}.")

    if args.get("cookie") is not None:
        print(f"Using 2FA cookie {args.get('cookie')}.")

    if args.get("verbose") > 0:
        logging.basicConfig(level=logging.DEBUG)

    async with aiohttp.ClientSession() as session:
        alarm = ADCController(
            args.get("username"),
            args.get("password"),
            session,
            False,  # ForceBypass
            False,  # NoEntryDelay
            False,  # SilentArming
            args.get("cookie"),
        )

        await alarm.async_login()

        print(f"\nProvider: {alarm.provider_name}")
        print(f"Logged in as: {alarm.user_email} ({alarm.user_id})")

        print("\n*** SYSTEMS ***\n")
        if len(alarm.systems) == 0:
            print("(none found)")
        else:
            for element in alarm.systems:
                _print_element_tearsheet(element)

        print("\n*** PARTITIONS ***\n")
        if len(alarm.partitions) == 0:
            print("(none found)")
        else:
            for element in alarm.partitions:
                _print_element_tearsheet(element)

        print("\n*** SENSORS ***\n")
        if len(alarm.sensors) == 0:
            print("(none found)")
        else:
            for element in alarm.sensors:
                _print_element_tearsheet(element)

        print("\n*** LOCKS ***\n")
        if len(alarm.locks) == 0:
            print("(none found)")
        else:
            for element in alarm.locks:
                _print_element_tearsheet(element)

        print("\n*** GARAGE DOORS ***\n")
        if len(alarm.garage_doors) == 0:
            print("(none found)")
        else:
            for element in alarm.garage_doors:
                _print_element_tearsheet(element)

        print("\n")


def _print_element_tearsheet(element: ADCBaseElement):
    if element.battery_critical:
        battery = "Critical"
    elif element.battery_low:
        battery = "Low"
    else:
        battery = "Normal"

    malfunction = "\n   ~~MALFUNCTIONING~~" if element.malfunction else ""

    subtype = (
        f"\n        Sensor Type: {element.device_subtype.name}"
        if hasattr(element, "device_subtype")
        else ""
    )

    print(
        f"""{element.name} ({element.id_}){malfunction}{subtype}
        State: {element.state}
        Battery: {battery}"""
    )


if __name__ == "__main__":
    asyncio.run(main())
