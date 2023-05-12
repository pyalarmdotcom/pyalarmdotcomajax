"""Test sensor devices."""

import json

import pytest
from deepdiff import DeepDiff

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices.water_sensor import WaterSensor
from tests.responses import get_http_body_json


@pytest.mark.asyncio
async def test__individual_sensors(
    all_base_ok_responses: str,
    adc_client: AlarmController,
) -> None:
    """Test for function that fetches item metadata from Alarm.com API."""

    await adc_client.async_update()

    src_devices = [
        device["id"]
        for device in json.loads(get_http_body_json("device_catalog_ok")).get("included", {})
        if device.get("type") == "devices/sensor"
    ]

    # Account for all source devices in response.
    assert not (
        diff := DeepDiff(src_devices, list(adc_client.devices.sensors.keys()), ignore_order=True)
    ), f"Difference: {diff}"


@pytest.mark.asyncio
async def test__water_sensor__state__ok(
    all_base_ok_responses: str,
    response_mocker: str,
    adc_client: AlarmController,
) -> None:
    """Ensures that WaterSensor states inherit Sensor states."""

    await adc_client.async_update()

    assert adc_client.devices.water_sensors.values()

    for water_sensor in adc_client.devices.water_sensors.values():
        assert type(water_sensor) == WaterSensor
        assert water_sensor.state in [WaterSensor.DeviceState.DRY, WaterSensor.DeviceState.WET]
