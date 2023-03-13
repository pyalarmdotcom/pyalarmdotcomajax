"""Global fixture functions."""

# pylint: disable = redefined-outer-name

from collections.abc import AsyncGenerator, Generator

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
def all_base_ok_responses(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ############
    ### META ###
    ############

    response_mocker.get(
        url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("trouble_condition_ok"),
        repeat=True,
    )
    response_mocker.get(
        url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("identity_ok"),
        repeat=True,
    )

    ###############
    ### DEVICES ###
    ###############

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("sensor_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.CAMERA)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("camera_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GARAGE_DOOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("garage_door_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GATE)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("gate_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("image_sensor_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["additional"][
            "recent_images"
        ].format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("image_sensor_data_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LIGHT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("light_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LOCK)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("lock_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.PARTITION)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("partition_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("system_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.THERMOSTAT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("thermostat_ok"),
        repeat=True,
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.WATER_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("water_sensor_ok"),
        repeat=True,
    )


@pytest.fixture
def all_extension_ok_responses(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ##################
    ### EXTENSIONS ###
    ##################

    response_mocker.get(
        url=CameraSkybellControllerExtension.ENDPOINT,
        status=200,
        body=get_http_body_html("camera_settings_skybell"),
    )


@pytest.fixture
def skybell_missing_video_quality_field(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ##################
    ### EXTENSIONS ###
    ##################

    response_mocker.get(
        url=CameraSkybellControllerExtension.ENDPOINT,
        status=200,
        body=get_http_body_html("camera_settings_skybell_missing_video_quality_field"),
    )


@pytest.fixture
def camera_no_permissions(response_mocker: aioresponses) -> None:
    """No permissions for camera or invalid afg cookie."""

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.CAMERA)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("no_permissions_or_invalid_antiforgery"),
    )


@pytest.fixture
def all_base_ok_camera_403(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ############
    ### META ###
    ############

    response_mocker.get(
        url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("trouble_condition_ok"),
    )
    response_mocker.get(
        url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("identity_ok"),
    )

    ###############
    ### DEVICES ###
    ###############

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.CAMERA)["primary"].format(
            c.URL_BASE, ""
        ),
        status=403,
        body=get_http_body_html("404"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GARAGE_DOOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("garage_door_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GATE)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("gate_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("image_sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["additional"][
            "recent_images"
        ].format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("image_sensor_data_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LIGHT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("light_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LOCK)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("lock_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.PARTITION)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("partition_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("system_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.THERMOSTAT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("thermostat_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.WATER_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("water_sensor_ok"),
    )


@pytest.fixture
def all_base_ok_camera_404(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    ############
    ### META ###
    ############

    response_mocker.get(
        url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("trouble_condition_ok"),
    )
    response_mocker.get(
        url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("identity_ok"),
    )

    ###############
    ### DEVICES ###
    ###############

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.CAMERA)["primary"].format(
            c.URL_BASE, ""
        ),
        status=404,
        body=get_http_body_html("404"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GARAGE_DOOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("garage_door_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GATE)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("gate_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("image_sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["additional"][
            "recent_images"
        ].format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("image_sensor_data_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LIGHT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("light_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LOCK)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("lock_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.PARTITION)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("partition_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("system_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.THERMOSTAT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("thermostat_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.WATER_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("water_sensor_ok"),
    )


@pytest.fixture
def successful_init_lock_refresh_fail(response_mocker: aioresponses) -> None:
    """Shortcut for including all mocked success responses."""

    #################
    ### FIRST RUN ###
    #################

    ############
    ### META ###
    ############

    response_mocker.get(
        url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("trouble_condition_ok"),
    )
    response_mocker.get(
        url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("identity_ok"),
    )

    ###############
    ### DEVICES ###
    ###############

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.CAMERA)["primary"].format(
            c.URL_BASE, ""
        ),
        status=404,
        body=get_http_body_html("404"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GARAGE_DOOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("garage_door_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GATE)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("gate_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("image_sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["additional"][
            "recent_images"
        ].format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("image_sensor_data_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LIGHT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("light_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LOCK)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("lock_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.PARTITION)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("partition_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("system_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.THERMOSTAT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("thermostat_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.WATER_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("water_sensor_ok"),
    )

    ##################
    ### SECOND RUN ###
    ##################

    ############
    ### META ###
    ############

    response_mocker.get(
        url=c.TROUBLECONDITIONS_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("trouble_condition_ok"),
    )
    response_mocker.get(
        url=c.IDENTITIES_URL_TEMPLATE.format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("identity_ok"),
    )

    ###############
    ### DEVICES ###
    ###############

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.CAMERA)["primary"].format(
            c.URL_BASE, ""
        ),
        status=404,
        body=get_http_body_html("404"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GARAGE_DOOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("garage_door_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.GATE)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("gate_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("image_sensor_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.IMAGE_SENSOR)["additional"][
            "recent_images"
        ].format(c.URL_BASE, ""),
        status=200,
        body=get_http_body_json("image_sensor_data_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LIGHT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("light_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.LOCK)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("no_permissions_or_invalid_antiforgery"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.PARTITION)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("partition_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.SYSTEM)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("system_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.THERMOSTAT)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("thermostat_ok"),
    )

    response_mocker.get(
        url=AttributeRegistry.get_endpoints(DeviceType.WATER_SENSOR)["primary"].format(
            c.URL_BASE, ""
        ),
        status=200,
        body=get_http_body_json("water_sensor_ok"),
    )
