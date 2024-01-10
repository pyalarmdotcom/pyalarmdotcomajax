"""Representations of API objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from mashumaro import field_options
from mashumaro.mixins.json import DataClassJSONMixin

###################
# API BASE ENTITY #
###################


@dataclass
class BaseElement(DataClassJSONMixin):
    """Base class for API elements."""

    class Config:
        """Mashumaro settings for API elements."""

        serialize_by_alias = True


EntityTypeT = TypeVar("EntityTypeT")


@dataclass
class GenericEntityStub(BaseElement, Generic[EntityTypeT]):
    """Barebones representation of an entity. Often used in relationships lists."""

    id_: int = field(metadata=field_options(alias="id"))
    type_: EntityTypeT = field(metadata=field_options(alias="type"))


Attributes = dict[str, Any]
AttributesT = TypeVar("AttributesT")


@dataclass
class GenericEntity(BaseElement, Generic[EntityTypeT, AttributesT]):
    """Full entity description that contains, id, type, attributes, and relationships."""

    id_: int = field(metadata=field_options(alias="id"))
    type_: EntityTypeT = field(metadata=field_options(alias="type"))
    attributes: AttributesT
    relationships: dict[str, GenericEntityStub] | None = None


Entity = GenericEntity[Attributes, str]


@dataclass
class GenericResponse(BaseElement, Generic[EntityTypeT, AttributesT]):
    """Top level container for all API responses. Includes single-item and multi-item responses."""

    data: GenericEntity[EntityTypeT, AttributesT] | list[GenericEntity[EntityTypeT, AttributesT]]
    included: list[Entity] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


Response = GenericResponse[str, Entity]
