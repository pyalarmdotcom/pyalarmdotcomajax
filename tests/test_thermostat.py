"""Test thermostat device."""

import pytest

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.cli import _print_element_tearsheet
from pyalarmdotcomajax.devices.thermostat import Thermostat


@pytest.mark.asyncio  # type: ignore
async def test__device_thermostat__ok(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    response_mocker: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Ensures that thermostats load correctly."""

    await adc_client.async_update()

    assert adc_client.thermostats[0]

    thermostat = adc_client.thermostats[0]

    assert thermostat is not None
    assert thermostat.name == "Upstairs"

    assert thermostat.attributes is not None
    assert thermostat.attributes.temp_at_tstat == 72
    assert thermostat.attributes.temp_average == 72
    assert thermostat.attributes.supports_fan_mode is True
    assert thermostat.attributes.supports_fan_indefinite is False
    assert thermostat.attributes.supports_fan_circulate_when_off is False
    assert thermostat.attributes.supported_fan_durations == [1, 2, 3, 24]
    assert thermostat.attributes.fan_mode == Thermostat.FanMode.AUTO
    assert thermostat.attributes.supports_heat is True
    assert thermostat.attributes.supports_heat_aux is False
    assert thermostat.attributes.supports_cool is True
    assert thermostat.attributes.supports_auto is True
    assert thermostat.attributes.setpoint_buffer == 6.0
    assert thermostat.attributes.min_heat_setpoint == 45
    assert thermostat.attributes.min_cool_setpoint == 65
    assert thermostat.attributes.max_heat_setpoint == 79
    assert thermostat.attributes.max_cool_setpoint == 92
    assert thermostat.attributes.heat_setpoint == 68
    assert thermostat.attributes.cool_setpoint == 73
    assert thermostat.attributes.supports_setpoints is True
    assert thermostat.attributes.supports_humidity is False
    assert thermostat.attributes.humidity == 69
    assert thermostat.attributes.supports_schedules is True
    assert thermostat.attributes.supports_schedules_smart is False
    assert thermostat.attributes.schedule_mode == Thermostat.ScheduleMode.SCHEDULED


@pytest.mark.asyncio  # type: ignore
async def test__device_thermostat__cli_tearsheet(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """_print_element_tearsheet will throw exception on failure."""

    await adc_client.async_update()

    assert adc_client.thermostats[0]

    _print_element_tearsheet(adc_client.thermostats[0])
