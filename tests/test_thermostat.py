"""Test thermostat device."""

from pyalarmdotcomajax import AlarmController
import pytest


@pytest.mark.asyncio  # type: ignore
async def test__device_thermostat__ok(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    response_mocker: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Ensures that pyalarmdotcomajax skips loading data from Skybell HD if Skybell HD config page has unexpected structure."""

    await adc_client.async_update()

    assert adc_client.thermostats[0]

    thermostat = adc_client.thermostats[0]

    assert thermostat.name == "Upstairs Thermostat"
