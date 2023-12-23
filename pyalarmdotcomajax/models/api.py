"""Representations of API objects."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ApiAttributes(BaseModel):
    """Base attributes for a single entity."""

    class Config:
        """pydantic config."""

        allow_population_by_field_name = True


ApiAttributesT = TypeVar("ApiAttributesT", bound=ApiAttributes)
ApiEntityTypeT = TypeVar("ApiEntityTypeT", bound=str)


class ApiBaseEntity(BaseModel, Generic[ApiEntityTypeT]):
    """Barebones representation of an entity. Often used in relationships lists."""

    id_: int = Field(alias="id")
    type_: ApiEntityTypeT = Field(alias="type")

    class Config:
        """pydantic config."""

        allow_population_by_field_name = True


class ApiEntity(ApiBaseEntity, Generic[ApiEntityTypeT, ApiAttributesT]):
    """Full entity description that contains, id, type, attributes, and relationships."""

    attributes: ApiAttributesT
    relationships: dict[str, ApiBaseEntity] | None = None


class ApiResponse(BaseModel, Generic[ApiEntityTypeT, ApiAttributesT]):
    """Top level container for all API responses. Includes single-item and multi-item responses."""

    model_config = ConfigDict(
        extra="allow",
    )
    data: ApiEntity[ApiEntityTypeT, ApiAttributesT] | list[ApiEntity[ApiEntityTypeT, ApiAttributesT]]
    included: list[ApiEntity] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
