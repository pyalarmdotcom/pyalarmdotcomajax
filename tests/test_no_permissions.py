"""Tests for main controller."""

# pylint: disable=protected-access

import pytest

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.devices import DeviceType


@pytest.mark.asyncio  # type: ignore
async def test__async_build_device_list__cameras(
    camera_no_permissions: pytest.fixture,
    all_base_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test for function that fetches item metadata from Alarm.com API."""

    items = await adc_client._async_build_device_list(DeviceType.CAMERA)

    assert items == []


@pytest.mark.asyncio  # type: ignore
async def test___async_build_device_list__cameras(
    camera_no_permissions: pytest.fixture,
    all_base_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test _async_build_device_list for account without camera service."""

    await adc_client._async_build_device_list(DeviceType.CAMERA)

    assert adc_client.cameras == []


@pytest.mark.asyncio  # type: ignore
async def test___async_update__no_permissions(
    all_base_ok_camera_403: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test that 403 for one device type doesn't impede downstream device types from loading."""

    await adc_client.async_update()

    assert adc_client.systems
    assert adc_client.partitions
    assert adc_client.sensors
    assert adc_client.locks
    assert adc_client.garage_doors
    assert adc_client.image_sensors
    assert adc_client.lights
    assert adc_client.thermostats
    assert adc_client.water_sensors
    assert not adc_client.cameras


@pytest.mark.asyncio  # type: ignore
async def test___async_update__invalid_endpoint(
    all_base_ok_camera_404: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test that 403 for one device type doesn't impede downstream device types from loading."""

    await adc_client.async_update()

    assert adc_client.systems
    assert adc_client.partitions
    assert adc_client.sensors
    assert adc_client.locks
    assert adc_client.garage_doors
    assert adc_client.image_sensors
    assert adc_client.lights
    assert adc_client.thermostats
    assert adc_client.water_sensors
    assert not adc_client.cameras


@pytest.mark.asyncio  # type: ignore
async def test___async_update__lock_refresh_failure(
    successful_init_lock_refresh_fail: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Test for when devices initialize but fail to refresh. Ensure that devices are wiped on update failure."""

    await adc_client.async_update()

    assert adc_client.systems
    assert adc_client.partitions
    assert adc_client.sensors
    assert adc_client.locks
    assert adc_client.garage_doors
    assert adc_client.image_sensors
    assert adc_client.lights
    assert adc_client.thermostats
    assert adc_client.water_sensors

    await adc_client.async_update()

    assert adc_client.systems
    assert adc_client.partitions
    assert adc_client.sensors
    assert not adc_client.locks
    assert adc_client.garage_doors
    assert adc_client.image_sensors
    assert adc_client.lights
    assert adc_client.thermostats
    assert adc_client.water_sensors
