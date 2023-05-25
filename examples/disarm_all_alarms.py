"""Example for retrieving data for all alarm control panels (partitions) and submitting disarm requests."""

# #
# WARNING: THIS SCRIPT WILL DISARM ALL OF YOUR ARMED ALARMS
# #

import asyncio
import sys

import aiohttp

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices.partition import Partition
from pyalarmdotcomajax.exceptions import UnexpectedResponse, NotAuthorized, AuthenticationFailed

USERNAME = "ENTER YOUR USERNAME"
PASSWORD = "ENTER YOUR PASSWORD"
TWOFACTOR = "YOUR 2FA COOKIE"  # Required if two factor authentication is enabled on your account.


async def main() -> None:
    """Request Alarm.com sensor data."""
    async with aiohttp.ClientSession() as session:
        alarm = AlarmController(
            username=USERNAME,
            password=PASSWORD,
            websession=session,
            twofactorcookie=TWOFACTOR or None,
        )

        try:
            await alarm.async_login()
            await alarm.async_update()
        except AuthenticationFailed:
            print("Failed to login. Your credentials are incorrect.")
            sys.exit()
        except NotAuthorized:
            print("Encountered permission error while retrieving data.")
            sys.exit()
        except (aiohttp.ClientError, asyncio.TimeoutError, UnexpectedResponse):
            print("Failed to login. Could not establish a connection to the Alarm.com server.")
            sys.exit()

        for partition in alarm.devices.partitions.values():
            if isinstance(partition.state, Partition.DeviceState) is True and (
                Partition.DeviceState(partition.state) != Partition.DeviceState.DISARMED
            ):
                print(f"Alarm control panel {partition.name} is currently armed. Disarming...")
                try:
                    await partition.async_disarm()
                    print("Disarmed successfully.")
                except NotAuthorized:
                    print(
                        "Failed to disarm. Your Alarm.com user does not have permission to change the state of"
                        " this control panel."
                    )
                except AuthenticationFailed:
                    print("Failed to disarm. Your credentials are incorrect.")
                except (asyncio.TimeoutError, aiohttp.ClientError, UnexpectedResponse):
                    print("Failed to disarm. Could not establish a connection to the Alarm.com server.")
            else:
                print(f"Alarm control panel {partition.name} is already disarmed. Nothing to do here...")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
