"""Test partition device."""

# ruff: noqa: PLR2004

from collections import Counter

import pytest

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.cli import _print_element_tearsheet
from pyalarmdotcomajax.devices.partition import Partition


@pytest.mark.asyncio
async def test__device_partition__house__ok(
    all_base_ok_responses: str,
    adc_client: AlarmController,
) -> None:
    """Ensures that partitions load correctly."""

    await adc_client.async_update()

    assert adc_client.devices.partitions["id-partition-house"]

    partition = adc_client.devices.partitions["id-partition-house"]

    assert partition is not None
    assert partition.name == "House"

    assert partition.attributes is not None

    if partition.attributes.extended_arming_options is not None:
        # Counter allows for comparing lists while ignoring order.
        assert Counter(partition.attributes.extended_arming_options.arm_away) == Counter(
            [
                Partition.ExtendedArmingOption.NO_ENTRY_DELAY,
                Partition.ExtendedArmingOption.SILENT_ARMING,
                Partition.ExtendedArmingOption.BYPASS_SENSORS,
                Partition.ExtendedArmingOption.SELECTIVE_BYPASS,
            ]
        )


@pytest.mark.asyncio
async def test__device_partition__garage__ok(
    all_base_ok_responses: str,
    response_mocker: str,
    adc_client: AlarmController,
) -> None:
    """Ensures that partitions load correctly."""

    await adc_client.async_update()

    assert adc_client.devices.partitions["id-partition-detached_garage"]

    partition = adc_client.devices.partitions["id-partition-detached_garage"]

    assert partition is not None
    assert partition.name == "Detached Garage"

    assert partition.attributes is not None

    if partition.attributes.extended_arming_options is not None:
        # Counter allows for comparing lists while ignoring order.
        assert Counter(partition.attributes.extended_arming_options.arm_away) == Counter(
            [
                Partition.ExtendedArmingOption.NO_ENTRY_DELAY,
                Partition.ExtendedArmingOption.SILENT_ARMING,
            ]
        )


@pytest.mark.asyncio
async def test__device_partition__cli_tearsheet(
    all_base_ok_responses: str,
    adc_client: AlarmController,
) -> None:
    """_print_element_tearsheet will throw exception on failure."""

    await adc_client.async_update()

    assert len(adc_client.devices.partitions) == 2

    _print_element_tearsheet(adc_client.devices.partitions["id-partition-house"])
