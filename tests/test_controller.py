"""Tests for main controller."""

# pylint: disable=protected-access

import json
from collections.abc import Callable

import aiohttp
import pytest
from deepdiff import DeepDiff

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices import DeviceType
from tests.responses import get_http_body_json


def test_property__initial_state(adc_client: AlarmController) -> None:
    """Ensure that login data is ingested correctly."""
    assert adc_client._password == "hunter2"
    assert adc_client._username == "test-username"
    assert adc_client.two_factor_cookie == "test-cookie"
    assert isinstance(adc_client._websession, aiohttp.ClientSession)

    assert adc_client.provider_name is None
    assert adc_client.user_id is None

    assert not adc_client.devices.systems.values()
    assert not adc_client.devices.partitions.values()
    assert not adc_client.devices.sensors.values()
    assert not adc_client.devices.locks.values()
    assert not adc_client.devices.garage_doors.values()
    assert not adc_client.devices.image_sensors.values()
    assert not adc_client.devices.lights.values()
    assert not adc_client.devices.thermostats.values()
    assert not adc_client.devices.cameras.values()
    assert not adc_client.devices.water_sensors.values()


@pytest.mark.asyncio
async def test__async_build_device_list__sensor_metadata(
    all_base_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test for function that fetches item metadata from Alarm.com API."""

    items = await adc_client._async_build_device_list(DeviceType.SENSOR)

    for rsp_device, _ in items:
        src_match = {}

        for src_device in json.loads(get_http_body_json("sensor_ok")).get("data", {}):
            if src_device.get("id") == rsp_device.get("id"):
                src_match = src_device

        # Account for all source devices in response.
        assert not (
            diff := DeepDiff(src_match, rsp_device, ignore_order=True)
        ), f"Difference: {diff}"


@pytest.mark.asyncio
async def test___async_build_device_list__sensors(
    all_base_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test whether pyalarmdotcomajax sensor objects are built."""

    await adc_client.async_update(DeviceType.SENSOR)

    print(adc_client.devices.sensors.values())

    assert adc_client.devices.sensors.values()


@pytest.mark.asyncio
async def test___async_update__ok(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test whether pyalarmdotcomajax sensor objects are built."""

    await adc_client.async_update()

    assert adc_client.devices.systems.values()
    assert adc_client.devices.partitions.values()
    assert adc_client.devices.sensors.values()
    assert adc_client.devices.locks.values()
    assert adc_client.devices.garage_doors.values()
    assert adc_client.devices.image_sensors.values()
    assert adc_client.devices.lights.values()
    assert adc_client.devices.thermostats.values()
    assert adc_client.devices.cameras.values()
    assert adc_client.devices.water_sensors.values()
