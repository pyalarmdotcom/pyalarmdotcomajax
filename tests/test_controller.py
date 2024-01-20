"""Tests for main controller."""

# pylint: disable=protected-access
# ruff: noqa: SLF001, S105

import aiohttp
import pytest

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.exceptions import UnexpectedResponse


def test_property__initial_state(adc_client: AlarmController) -> None:
    """Ensure that login data is ingested correctly."""
    assert adc_client._password == "hunter2"
    assert adc_client._username == "test-username"
    assert adc_client.two_factor_cookie == "test-cookie"
    assert isinstance(adc_client._websession, aiohttp.ClientSession)

    assert adc_client.provider_name is None
    assert adc_client.user_id is None

    assert not adc_client.devices.all.values()


@pytest.mark.asyncio
async def test__device_storage(
    all_base_ok_responses: str,
    adc_client: AlarmController,
) -> None:
    """Test for function that fetches item metadata from Alarm.com API."""

    await adc_client.async_update()

    assert adc_client.devices.systems.values()
    assert adc_client.devices.partitions.values()
    assert adc_client.devices.sensors.values()
    assert adc_client.devices.locks.values()
    assert adc_client.devices.garage_doors.values()
    assert adc_client.devices.image_sensors.values()
    assert adc_client.devices.lights.values()
    assert adc_client.devices.thermostats.values()
    assert adc_client.devices.water_sensors.values()


@pytest.mark.asyncio
async def test___async_update__refresh_failure(
    device_catalog_no_permissions: str,
    adc_client: AlarmController,
) -> None:
    """Test for when devices initialize but fail to refresh. Ensure that devices are wiped on update failure."""

    with pytest.raises(UnexpectedResponse):
        await adc_client.async_update()


@pytest.mark.asyncio
async def test__async_has_image_sensors(
    image_sensors_no_permission: str,
    all_base_ok_responses: str,
    adc_client: AlarmController,
) -> None:
    """Test for function that fetches image sensor images."""

    await adc_client.async_update()
