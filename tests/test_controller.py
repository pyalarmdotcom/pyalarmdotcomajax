"""Tests for main controller."""

# pylint: disable=protected-access

import json

import aiohttp
from deepdiff import DeepDiff
from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices import DeviceType
import pytest
from tests.responses import get_http_body_json


def test_property__initial_state(adc_client: AlarmController) -> None:
    """Ensure that login data is ingested correctly."""
    assert adc_client._password == "hunter2"
    assert adc_client._username == "test-username"
    assert adc_client.two_factor_cookie == "test-cookie"
    assert isinstance(adc_client._websession, aiohttp.ClientSession)

    assert adc_client.provider_name is None
    assert adc_client.user_id is None

    assert not adc_client.systems
    assert not adc_client.partitions
    assert not adc_client.sensors
    assert not adc_client.locks
    assert not adc_client.garage_doors
    assert not adc_client.image_sensors
    assert not adc_client.lights


@pytest.mark.asyncio  # type: ignore
async def test__async_get_items_and_subordinates__sensors(
    all_base_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test for function that fetches item metadata from Alarm.com API."""

    items = await adc_client._async_get_items_and_subordinates(DeviceType.SENSOR)

    for rsp_device, _ in items:

        src_match = {}

        for src_device in json.loads(get_http_body_json("sensor_ok")).get("data", {}):
            if src_device.get("id") == rsp_device.get("id"):
                src_match = src_device

        # Account for all source devices in response.
        assert not (
            diff := DeepDiff(src_match, rsp_device, ignore_order=True)
        ), f"Difference: {diff}"


@pytest.mark.asyncio  # type: ignore
async def test___async_get_and_build_devices__sensors(
    all_base_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test whether pyalarmdotcomajax sensor objects are built."""

    await adc_client._async_get_and_build_devices([DeviceType.SENSOR])

    assert adc_client.sensors
