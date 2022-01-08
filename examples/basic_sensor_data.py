"""Basic example for using pyalarmdotcomajax."""

from pyalarmdotcomajax import ADCController
import aiohttp
import asyncio

username = "ENTER YOUR USERNAME"
password = "ENTER YOUR PASSWORD"
twofactor = "YOUR 2FA COOKIE"  # Required if two factor authentication is enabled on your account.


async def main():
    async with aiohttp.ClientSession() as session:

        # Use ADCControllerADT for ADT, ADCControllerProtection1 for Protection1, ADCController for all other providers.

        alarm = ADCController(
            username=username,
            password=password,
            websession=session,
            forcebypass=False,
            noentrydelay=False,
            silentarming=False,
            twofactorcookie=twofactor,
        )

        await alarm.async_login()

        for sensor in alarm.sensors:
            print(
                f"Name: {sensor.name}, Sensor Type: {sensor.device_subtype}, State: {sensor.state}"
            )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
