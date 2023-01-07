"""Test partition device."""

from collections import Counter

import pytest

from pyalarmdotcomajax import AlarmController
from pyalarmdotcomajax.cli import _print_element_tearsheet
from pyalarmdotcomajax.devices.partition import Partition


@pytest.mark.asyncio  # type: ignore
async def test__device_partition__ok(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    response_mocker: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """Ensures that partitions load correctly."""

    await adc_client.async_update()

    assert adc_client.partitions[0]

    partition = adc_client.partitions[0]

    assert partition is not None
    assert partition.name == "Alarm"

    assert partition.attributes is not None

    if partition.attributes.extended_arming_options is not None:
        # Counter allows for comparing lists while ignoring order.
        assert Counter(
            partition.attributes.extended_arming_options.armed_away
        ) == Counter(
            [
                Partition.ExtendedArmingOption.NO_ENTRY_DELAY,
                Partition.ExtendedArmingOption.SILENT_ARMING,
            ]
        )


@pytest.mark.asyncio  # type: ignore
async def test__device_partition__cli_tearsheet(
    all_base_ok_responses: pytest.fixture,
    all_extension_ok_responses: pytest.fixture,
    adc_client: AlarmController,
) -> None:
    """_print_element_tearsheet will throw exception on failure."""

    await adc_client.async_update()

    assert adc_client.partitions[0]

    _print_element_tearsheet(adc_client.partitions[0])
