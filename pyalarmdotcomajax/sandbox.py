"""Sandbox."""

# ruff: noqa: T201

from __future__ import annotations

import logging
import os
import sys

import aiohttp
from termcolor import cprint

from pyalarmdotcomajax import AlarmBridge, GarageDoorController
from pyalarmdotcomajax.adc.util import summarize_cli_actions
from pyalarmdotcomajax.controllers.base import BaseController
from pyalarmdotcomajax.controllers.thermostats import ThermostatController
from pyalarmdotcomajax.exceptions import (
    AuthenticationFailed,
    ConfigureTwoFactorAuthentication,
    NotAuthorized,
    OtpRequired,
    UnexpectedResponse,
)

log = logging.getLogger(__name__)

cli_actions = summarize_cli_actions(GarageDoorController)
for method_name in cli_actions.items():
    print(f"method: {method_name}")

print(summarize_cli_actions(ThermostatController, include_params=True))
# for method, description in cli_actions.items():
#     print(f"method: {method}, description: {description}")


async def main() -> None:
    """Run application."""

    # Get the credentials from environment variables
    username = str(os.environ.get("ADC_USERNAME"))
    password = str(os.environ.get("ADC_PASSWORD"))
    mfa_token = str(os.environ.get("ADC_COOKIE"))

    bridge = AlarmBridge(username, password, mfa_token)

    #
    # LOG IN
    #

    try:
        # Initialize the connector
        await bridge.initialize()

    except ConfigureTwoFactorAuthentication:
        cprint("Unable to log in. Please set up two-factor authentication for this account.", "red")
        sys.exit()

    except (TimeoutError, aiohttp.ClientError, UnexpectedResponse, NotAuthorized):
        cprint("Could not connect to Alarm.com.", "red")
        sys.exit()

    except AuthenticationFailed:
        cprint("Invalid credentials.", "red")
        sys.exit()

    #
    # HANDLE MFA
    #

    except OtpRequired:
        raise

    for controller in BaseController.__subclasses__():
        if len(summary := summarize_cli_actions(controller, include_params=True)):
            print(f"{controller.resource_type.name}: {summary}")
            print()

    await bridge.close()


# Start the asyncio task
# if __name__ == "__main__":
# asyncio.run(main())
