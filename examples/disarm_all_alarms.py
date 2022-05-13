"""Example for retrieving data for all alarm control panels (partitions) and submitting disarm requests."""

# #
# WARNING: THIS SCRIPT WILL DISARM ALL OF YOUR ARMED ALARMS
# #

import asyncio
from multiprocessing import AuthenticationError
import sys

import aiohttp
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices import Partition

USERNAME = "ENTER YOUR USERNAME"
PASSWORD = "ENTER YOUR PASSWORD"
TWOFACTOR = (  # Required if two factor authentication is enabled on your account.
    "YOUR 2FA COOKIE"
)


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
        except AuthenticationError:
            print("Failed to login. Your credentials are incorrect.")
            sys.exit()
        except ConnectionError:
            print(
                "Failed to login. Could not establish a connection to the Alarm.com"
                " server."
            )
            sys.exit()

        for partition in alarm.partitions:
            if isinstance(partition.state, Partition.DeviceState) is True and (
                Partition.DeviceState(partition.state) != Partition.DeviceState.DISARMED
            ):
                print(
                    f"Alarm control panel {partition.name} is currently armed."
                    " Disarming..."
                )
                try:
                    await partition.async_disarm()
                    print("Disarmed successfully.")
                except PermissionError:
                    print(
                        "Failed to disarm. Your Alarm.com user does not have permission"
                        " to change the state of this control panel."
                    )
                except AuthenticationError:
                    print("Failed to disarm. Your credentials are incorrect.")
                except ConnectionError:
                    print(
                        "Failed to disarm. Could not establish a connection to the"
                        " Alarm.com server."
                    )
            else:
                print(
                    f"Alarm control panel {partition.name} is already disarmed. Nothing"
                    " to do here..."
                )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
