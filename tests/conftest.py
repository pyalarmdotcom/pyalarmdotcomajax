"""Global fixture functions."""

# pylint: disable = redefined-outer-name

from collections.abc import AsyncGenerator, Callable, Generator

import aiohttp
import pytest
from aioresponses import aioresponses

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax import const as c
from pyalarmdotcomajax.devices.registry import AttributeRegistry, DeviceType
from pyalarmdotcomajax.extensions import CameraSkybellControllerExtension

from .responses import get_http_body_html, get_http_body_json


@pytest.fixture
def response_mocker() -> Generator:
    """Yield aioresponses."""
    with aioresponses() as mocker:
        yield mocker


@pytest.fixture
@pytest.mark.asyncio
async def adc_client() -> AsyncGenerator:
    """Build and return dummy controller for testing without Alarm.com API."""

    async with aiohttp.ClientSession() as websession:
        yield AlarmController(
            username="test-username",
            password="hunter2",  # noqa: S106
            websession=websession,
            twofactorcookie="test-cookie",
        )


@pytest.fixture
def all_base_ok_responses(response_mocker: aioresponses, all_base_ok_responses_callable: Callable) -> None:
    """Shortcut for including all mocked success responses immediately."""

    all_base_ok_responses_callable()


@pytest.fixture
def all_base_ok_responses_callable(response_mocker: aioresponses) -> Callable:
    """Shortcut for including all mocked success responses on demand."""

    def _load_mocks(repeat: bool = True) -> None:
        ############
        ### META ###
        ############

        response_mocker.get(
            url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
            status=200,
            body=get_http_body_json("trouble_conditions_ok"),
            repeat=repeat,
        )

        response_mocker.get(
            url=AlarmController.ALL_SYSTEMS_URL_TEMPLATE.format(c.URL_BASE),
            status=200,
            body=get_http_body_json("available_systems_ok"),
            repeat=repeat,
        )

        response_mocker.get(
            url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
            status=200,
            body=get_http_body_json("identities_ok"),
            repeat=repeat,
        )

        ###############
        ### DEVICES ###
        ###############

        response_mocker.get(
            url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(c.URL_BASE, "id-system"),
            status=200,
            body=get_http_body_json("system_ok"),
            repeat=repeat,
        )

        response_mocker.get(
            url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["primary"].format(c.URL_BASE, ""),
            status=200,
            body=get_http_body_json("image_sensors_ok"),
            repeat=repeat,
        )

        response_mocker.get(
            url=AlarmController.ALL_DEVICES_URL_TEMPLATE.format(c.URL_BASE, "id-system"),
            status=200,
            body=get_http_body_json("device_catalog_ok"),
            repeat=repeat,
        )

        response_mocker.get(
            url=AlarmController.ALL_RECENT_IMAGES_TEMPLATE.format(c.URL_BASE, ""),
            status=200,
            body=get_http_body_json("recent_images_ok"),
            repeat=repeat,
        )

        ##################
        ### EXTENSIONS ###
        ##################

        response_mocker.get(
            url=CameraSkybellControllerExtension.ENDPOINT.format(c.URL_BASE),
            status=200,
            body=get_http_body_html("camera_settings_skybell"),
            repeat=True,
        )

    return _load_mocks


@pytest.fixture
def image_sensors_no_permission(response_mocker: aioresponses, all_base_ok_responses_callable: Callable) -> None:
    """No permission to view devices."""

    response_mocker.get(
        url=AlarmController.ALL_RECENT_IMAGES_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("processing_error"),
        repeat=True,
    )

    all_base_ok_responses_callable()


@pytest.fixture
def skybell_missing_video_quality_field(
    response_mocker: aioresponses, all_base_ok_responses_callable: Callable
) -> None:
    """Shortcut for including all mocked success responses."""

    ##################
    ### EXTENSIONS ###
    ##################

    response_mocker.get(
        url=CameraSkybellControllerExtension.ENDPOINT.format(c.URL_BASE),
        status=200,
        body=get_http_body_html("camera_settings_skybell_missing_video_quality_field"),
        repeat=True,
    )

    all_base_ok_responses_callable()


@pytest.fixture
def device_catalog_no_permissions(response_mocker: aioresponses, all_base_ok_responses_callable: Callable) -> None:
    """Shortcut for including all mocked success responses."""

    response_mocker.get(
        url=AlarmController.ALL_DEVICES_URL_TEMPLATE.format(c.URL_BASE, "id-system"),
        status=200,
        body=get_http_body_json("no_permissions_or_invalid_antiforgery"),
        repeat=True,
    )

    all_base_ok_responses_callable()
