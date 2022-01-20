"""Basic example for getting sensor data via pyalarmdotcomajax."""

import asyncio

import aiohttp

from pyalarmdotcomajax import ADCController
from pyalarmdotcomajax.const import ArmingOption

USERNAME = "ENTER YOUR USERNAME"
PASSWORD = "ENTER YOUR PASSWORD"
TWOFACTOR = "YOUR 2FA COOKIE"  # Required if two factor authentication is enabled on your account.


async def main() -> None:
    """Request Alarm.com sensor data."""
    async with aiohttp.ClientSession() as session:

        alarm = ADCController(
            username=USERNAME,
            password=PASSWORD,
            websession=session,
            twofactorcookie=TWOFACTOR,
            forcebypass=ArmingOption.NEVER,
            noentrydelay=ArmingOption.NEVER,
            silentarming=ArmingOption.NEVER,
        )

        await alarm.async_login()

        for sensor in alarm.sensors:
            print(
                f"Name: {sensor.name}, Sensor Type: {sensor.device_subtype}, State: {sensor.state}"
            )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
