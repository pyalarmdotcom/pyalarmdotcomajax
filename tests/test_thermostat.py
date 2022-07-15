"""Test thermostat device."""

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.cli import _print_element_tearsheet
from pyalarmdotcomajax.devices.thermostat import Thermostat
import pytest


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
    assert thermostat.name == "Upstairs Thermostat"

    assert thermostat.attributes is not None
    assert thermostat.attributes.temp_at_tstat == 77
    assert thermostat.attributes.temp_average == 77
    assert thermostat.attributes.step_value == 1
    assert thermostat.attributes.supports_fan_mode is True
    assert thermostat.attributes.supports_fan_indefinite is False
    assert thermostat.attributes.supports_fan_circulate_when_off is True
    assert thermostat.attributes.supported_fan_durations == [1, 2, 3, 24]
    assert thermostat.attributes.fan_mode == Thermostat.FanMode.AUTO_LOW
    assert thermostat.attributes.fan_duration is None
    assert thermostat.attributes.supports_heat is True
    assert thermostat.attributes.supports_heat_aux is False
    assert thermostat.attributes.supports_cool is True
    assert thermostat.attributes.supports_auto is False
    assert thermostat.attributes.setpoint_buffer == 3
    assert thermostat.attributes.min_heat_setpoint == 40
    assert thermostat.attributes.min_cool_setpoint == 50
    assert thermostat.attributes.max_heat_setpoint == 90
    assert thermostat.attributes.max_cool_setpoint == 99
    assert thermostat.attributes.heat_setpoint == 71
    assert thermostat.attributes.cool_setpoint == 74
    assert thermostat.attributes.supports_setpoints is True
    assert thermostat.attributes.supports_humidity is False
    assert thermostat.attributes.humidity is None
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
