"""Test sensor devices."""

from collections.abc import Callable

import pytest

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices.sensor import Sensor
from pyalarmdotcomajax.devices.water_sensor import WaterSensor


@pytest.mark.asyncio
async def test__water_sensor__state__ok(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    response_mocker: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Ensures that WaterSensor states inherit Sensor states."""

    await adc_client.async_update()

    assert adc_client.devices.water_sensors.values()

    for water_sensor in adc_client.devices.water_sensors.values():
        assert isinstance(water_sensor, WaterSensor)
        assert isinstance(water_sensor.state, Sensor.DeviceState)
        assert water_sensor.state in [Sensor.DeviceState.DRY, Sensor.DeviceState.WET]
