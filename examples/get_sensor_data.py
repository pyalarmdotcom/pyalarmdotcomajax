"""Basic example for getting sensor data via pyalarmdotcomajax."""

import asyncio

import aiohttp

from pyalarmdotcomajax import AlarmController

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
            twofactorcookie=TWOFACTOR,
        )

        await alarm.async_login()
        await alarm.async_update()

        for sensor in alarm.sensors:
            print(
                f"Name: {sensor.name}, Sensor Type: {sensor.device_subtype}, State:"
                f" {sensor.state}"
            )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
