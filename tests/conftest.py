"""Global fixture functions."""

# pylint: disable = redefined-outer-name

from collections.abc import AsyncGenerator
from collections.abc import Generator

import aiohttp
from aioresponses import aioresponses
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.devices import DEVICE_URLS
from pyalarmdotcomajax.devices import DeviceType
from pyalarmdotcomajax.extensions import CameraSkybellControllerExtension
import pytest
from tests import responses


@pytest.fixture  # type: ignore
def response_mocker() -> Generator:
    """Yield aioresponses."""
    with aioresponses() as mocker:
        yield mocker


@pytest.fixture  # type: ignore
@pytest.mark.asyncio  # type: ignore
async def adc_client() -> AsyncGenerator:
    """Build and return dummy controller for testing without Alarm.com API."""

    async with aiohttp.ClientSession() as websession:
        yield AlarmController(
            username="test-username",
            password="hunter2",
            websession=websession,
            twofactorcookie="test-cookie",
        )


@pytest.fixture  # type: ignore
def all_base_ok_responses(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ############
    ### META ###
    ############

    response_mocker.get(
        url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=responses.TROUBLE_CONDITIONS_OK_RESPONSE_BODY,
    )
    response_mocker.get(
        url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=responses.IDENTITYS_OK_RESPONSE_BODY,
    )

    ###############
    ### DEVICES ###
    ###############

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.SENSOR]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.SENSORS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.CAMERA]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.CAMERAS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.GARAGE_DOOR]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.GARAGE_DOORS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.IMAGE_SENSOR]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.IMAGE_SENSORS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.IMAGE_SENSOR]["additional_endpoints"][
            "recent_images"
        ].format(c.URL_BASE, ""),
        status=200,
        body=responses.IMAGE_SENSORS_DATA_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.LIGHT]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.LIGHTS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.LOCK]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.LOCKS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.PARTITION]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.PARTITIONS_OK_RESPONSE_BODY,
    )

    response_mocker.get(
        url=DEVICE_URLS["supported"][DeviceType.SYSTEM]["endpoint"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=responses.SYSTEMS_OK_RESPONSE_BODY,
    )


@pytest.fixture  # type: ignore
def all_extension_ok_responses(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ##################
    ### EXTENSIONS ###
    ##################

    response_mocker.get(
        url=CameraSkybellControllerExtension.ENDPOINT,
        status=200,
        body=responses.SKYBELL_CONFIG_PAGE,
    )
