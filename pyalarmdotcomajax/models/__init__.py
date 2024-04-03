"""Alarm.com models."""

from __future__ import annotations

from dataclasses import dataclass, field

from mashumaro import field_options

from pyalarmdotcomajax.models.jsonapi import JsonApiBaseElement

from . import (  # noqa: F401
    auth,
    base,
    camera,
    device_catalog,
    garage_door,
    gate,
    image_sensor,
    light,
    lock,
    partition,
    sensor,
    system,
    thermostat,
    trouble_condition,
    user,
    water_sensor,
)


@dataclass
class AdcMiniSuccessResponse(JsonApiBaseElement):
    """
    Represents a success response object from Alarm.com "mini" endpoints.

    Includes:
    - WebSocket token
    - OTP Submission

    This response is not JSON:API compliant.

    Class will fail validation by AlarmBridge.request() if errors are present; response will then be processed as FailureDocument.
    """

    # fmt: off
    value: str | None = field(default=None)
    has_errors: bool = field(default=False)
    metadata: dict = field(default_factory=dict, metadata=field_options(alias="meta_data"))
    # fmt: on

    @classmethod
    def __post_deserialize__(cls, obj: AdcMiniSuccessResponse) -> AdcMiniSuccessResponse:
        """Validate values after deserialization."""

        if obj.has_errors:
            raise ValueError("Response has errors")

        return obj
