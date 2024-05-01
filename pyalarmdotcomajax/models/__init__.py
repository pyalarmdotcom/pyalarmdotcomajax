"""Alarm.com models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from mashumaro import field_options

from pyalarmdotcomajax.models.base import AdcDeviceResource, AdcResource, BaseManagedDeviceAttributes
from pyalarmdotcomajax.models.camera import Camera
from pyalarmdotcomajax.models.garage_door import GarageDoor
from pyalarmdotcomajax.models.gate import Gate
from pyalarmdotcomajax.models.image_sensor import ImageSensor
from pyalarmdotcomajax.models.jsonapi import Error, JsonApiBaseElement
from pyalarmdotcomajax.models.light import Light
from pyalarmdotcomajax.models.lock import Lock
from pyalarmdotcomajax.models.partition import Partition
from pyalarmdotcomajax.models.sensor import Sensor
from pyalarmdotcomajax.models.system import System
from pyalarmdotcomajax.models.thermostat import Thermostat
from pyalarmdotcomajax.models.trouble_condition import TroubleCondition
from pyalarmdotcomajax.models.user import Identity
from pyalarmdotcomajax.models.water_sensor import WaterSensor

__all__: tuple[str, ...] = (
    "Camera",
    "GarageDoor",
    "Gate",
    "ImageSensor",
    "Light",
    "Lock",
    "Partition",
    "Sensor",
    "System",
    "Thermostat",
    "TroubleCondition",
    "Identity",
    "WaterSensor",
)

AdcResourceT = TypeVar("AdcResourceT", bound=AdcResource)
AdcManagedDeviceT = TypeVar("AdcManagedDeviceT", bound=AdcDeviceResource[BaseManagedDeviceAttributes])


@dataclass
class AdcMiniSuccessResponse(JsonApiBaseElement):
    """
    Represents a success response object from Alarm.com "mini" endpoints.

    Includes:
    - WebSocket token
    - OTP Submission

    This response is not JSON:API compliant.

    Class will fail validation by AlarmBridge.request() if errors are present; response will then be processed as FailureDocument.

    This is likely a modified hapi/boom response object: https://hapi.dev/module/boom/api/?v=10.0.1
    """

    # fmt: off
    value: str | None = field(default=None)
    errors: list[Error] = field(default_factory=list)
    metadata: dict = field(default_factory=dict, metadata=field_options(alias="meta_data"))
    # fmt: on

    @classmethod
    def __post_deserialize__(cls, obj: AdcMiniSuccessResponse) -> AdcMiniSuccessResponse:
        """Validate values after deserialization."""

        if obj.errors:
            raise ValueError("Response has errors")

        return obj
