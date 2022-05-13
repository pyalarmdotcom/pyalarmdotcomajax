"""Test device extensions."""

import aiohttp
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.cli import _print_element_tearsheet
from pyalarmdotcomajax.extensions import CameraSkybellControllerExtension
from pyalarmdotcomajax.extensions import ConfigurationOptionType
from pyalarmdotcomajax.extensions import ExtendedProperties
import pytest

# pylint: disable=protected-access, missing-class-docstring, no-self-use


@pytest.mark.asyncio  # type: ignore
async def test__extension_camera_skybellhd__fetch(
    all_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Ensures that ExtendedProperties objects are created from server response data."""

    async with aiohttp.ClientSession() as websession:
        extension = CameraSkybellControllerExtension()
        configs: list[ExtendedProperties] = await extension.fetch(
            websession=websession, cookies={"foo": "bar"}
        )

    assert configs[0]["device_name"] == "Front Doorbell"
    assert configs[0]["config_id"] == "2048"
    assert configs[0]["settings"]["indoor_chime_on"]["current_value"] is True
    assert configs[0]["settings"]["outdoor_chime_on"]["current_value"] is False
    assert configs[0]["raw_attribs"]


@pytest.mark.asyncio  # type: ignore
async def test__extension_camera_skybellhd__via_alarm_controller(
    all_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test whether pyalarmdotcomajax camera objects are properly built when encountering Skybell HD cameras."""

    await adc_client.async_update()

    assert adc_client.cameras[0]

    skybell = adc_client.cameras[0]

    assert skybell.name == "Front Doorbell"
    assert skybell.settings["indoor_chime_on"]["current_value"] is True
    assert skybell.settings["outdoor_chime_on"]["current_value"] is False
    assert (
        skybell.settings["indoor_chime_on"]["option_type"]
        is ConfigurationOptionType.CHIME
    )


@pytest.mark.asyncio  # type: ignore
async def test__extension_camera_skybellhd__cli_tearsheet(
    all_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """_print_element_tearsheet will throw exception on failure."""

    await adc_client.async_update()

    assert adc_client.cameras[0]

    _print_element_tearsheet(adc_client.cameras[0])
