"""Representations of API objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

import humps
from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.types import Discriminator
from typing_extensions import TypeVar

###########################
# SCHEMA HELPER FUNCTOINS #
###########################


def page_number_from_link(link: Link | None | str) -> int | None:
    """
    Extract page number from links in a JSON:API response object.

    Returns page number if present, otherwise returns None.
    """

    return int(match.group(1)) if link and (match := re.search(r"page\[number\]=(\d+)", str(link))) else None


##########
# MIXINS #
##########


# @dataclass
# class CamelizerMixin:
#     """Convert keys between snake_case and camelCase."""

#     @classmethod
#     def __pre_deserialize__(cls, d: dict[Any, Any]) -> dict[Any, Any]:
#         """Pre-deserialization hook to convert keys from camelCase to snake case."""

#         print("pre_deserialize")

#         return {humps.decamelize(k): v for k, v in d.items()}

#     def __post_serialize__(self, d: dict[Any, Any]) -> dict[Any, Any]:
#         """Post-serialization hook to convert keys from snake_case to camelCase."""

#         print("pre_serialize")

#         return {humps.camelize(k): v for k, v in d.items()}


########################
# JSON:API BASE ENTITY #
########################


@dataclass
class JsonApiBaseElement(DataClassJSONMixin):
    """Base class for JSON:API elements."""

    @classmethod
    def __pre_deserialize__(cls, d: dict[Any, Any]) -> dict[Any, Any]:
        """Pre-deserialization hook to convert keys from camelCase to snake case."""

        return humps.decamelize(d)

    def __post_serialize__(self, d: dict[Any, Any]) -> dict[Any, Any]:
        """Post-serialization hook to convert keys from snake_case to camelCase."""

        return humps.camelize(d)

    class Config(BaseConfig):
        """Mashumaro settings for JSON:API elements."""

        serialize_by_alias = True


########################
# JSON:API CORE MODELS #
########################


@dataclass
class Meta(JsonApiBaseElement):
    """
    Represent non-standard meta-information that cannot be represented as an attribute or relationship.

    This meta-information can be used to include any additional information that does not fit within the standard JSON:API specification fields.
    """


@dataclass
class Link1(JsonApiBaseElement):
    """
    Define a detailed link object with href and optional meta-information.

    The link object is used to represent hyperlinks. The `href` attribute holds the URL of the link, and `meta` provides additional meta-information about the link.
    """

    href: str
    meta: Meta | None = None


Link = str | Link1

Attributes = dict[str, Any]


@dataclass
class Linkage(JsonApiBaseElement):
    """
    Define resource linkage to non-empty members in a relationship object.

    Resource linkage in a compound document allows resources to link in a standard way. Each linkage contains `type` and `id` members to identify linked resources uniquely.
    """

    id_: str = field(metadata=field_options(alias="id"))
    type_: str = field(metadata=field_options(alias="type"))
    meta: Meta | None = None


@dataclass
class Pagination(JsonApiBaseElement):
    """
    Provide pagination links for a collection of resources.

    Pagination is essential for handling large sets of data. This class includes `first`, `last`, `prev`, and `next` links to navigate through the data pages.
    """

    first: Link | None = None
    last: Link | None = None
    prev: Link | None = None
    next: Link | None = None


@dataclass
class Jsonapi(JsonApiBaseElement):
    """
    Describe the server's implementation of the JSON:API specification.

    This object includes information about the JSON:API version used by the server and any additional meta-information.
    """

    version: str | None = None
    meta: Meta | None = None


@dataclass
class Source(JsonApiBaseElement):
    """
    Identify the source of a problem in an error response.

    `pointer` is a JSON Pointer to the associated entity in the request document. `parameter` indicates which URI query parameter caused the error.
    """

    pointer: str | None = None
    parameter: str | None = None


@dataclass
class RelationshipLinks(JsonApiBaseElement):
    """
    Provide links for a relationship object in a resource.

    Relationships may reference other resource objects and are specified in a resource's links object. This class includes `self` and `related` links to manage the relationships.
    """

    self: Link | None = None
    related: Link | None = None


Links = dict[str, Link] | None

RelationshipToOne = None | Linkage

RelationshipToMany = list[Linkage]


@dataclass
class Error(JsonApiBaseElement):
    """
    Represent an error that occurred during a request.

    This class captures details about errors in a standardized format, including a unique ID, status code, error code, human-readable title and detail, source of the error, and any additional meta-information.
    """

    id_: str | None = field(metadata=field_options(alias="id"), default=None)
    links: Links | None = None
    status: str | None = None
    code: str | None = None
    title: str | None = None
    detail: str | None = None
    source: Source | None = None
    meta: Meta | None = None


@dataclass
class LinksModel(Pagination):
    """
    Extend the Pagination model to include other types of links.

    This class inherits from Pagination and may include additional links related to the primary data, following the JSON:API specification.
    """

    pass


@dataclass
class RelationshipsToData(JsonApiBaseElement):
    """
    Represent primary relationship data with optional links and meta-information.

    This class handles relationships that include direct data, optional links to related resources, and meta-information about the relationship.
    """

    data: RelationshipToOne | RelationshipToMany
    links: RelationshipLinks | None = None
    meta: Meta | None = None


@dataclass
class RelationshipstoMeta(JsonApiBaseElement):
    """
    Represent optional relationship data with meta-information and links.

    Similar to Relationships1 but allows for the relationship data to be optional. Includes meta-information and links related to the relationship.
    """

    meta: Meta
    links: RelationshipLinks | None = None
    data: RelationshipToOne | RelationshipToMany | None = None


@dataclass
class RelationshipstoLinks(JsonApiBaseElement):
    """
    Define a fully specified relationship with mandatory fields.

    This class represents a relationship that includes mandatory links, optional data, and meta-information, providing a complete structure for relationship representation.
    """

    links: RelationshipLinks
    data: RelationshipToOne | RelationshipToMany | None = None
    meta: Meta | None = None


Relationships = dict[str, RelationshipsToData | RelationshipstoLinks | RelationshipstoMeta]


@dataclass
class BaseAttributes(JsonApiBaseElement):
    """Base mashumaro settings for JSON:API attribute objects."""

    pass


AttributesT = TypeVar("AttributesT", bound=BaseAttributes)


@dataclass
class UnsupportedResource(JsonApiBaseElement):
    """
    Represent a single resource object in a JSON:API document.

    Resource objects are key constructs in JSON:API. They include a type, id, optional attributes, relationships, links, and meta-information.
    """

    supported: ClassVar[bool] = False

    type_: str = field(metadata=field_options(alias="type"))
    id_: str = field(metadata=field_options(alias="id"))
    attributes: Any
    links: Links | None = None
    meta: Meta | None = None
    relationships: Relationships | None = None


@dataclass
class BaseSupportedResource(UnsupportedResource):
    """
    Represent a single resource object in a JSON:API document.

    Resource objects are key constructs in JSON:API. They include a type, id, optional attributes, relationships, links, and meta-information.
    """

    supported: ClassVar[bool] = True
    attributes: BaseAttributes

    class Config(BaseConfig):
        """Mashumaro config for Resource."""

        # Allows aliased type_ attribute to be used as discriminator.
        discriminator = Discriminator(
            field="type",
            include_subtypes=True,
            include_supertypes=True,
            variant_tagger_fn=lambda cls: cls.type_,
        )


# ResourceT = TypeVar("ResourceT", bound=BaseSupportedResource)


# class JsonApiResponse(Generic[ResourceT], JsonApiBaseElement):
#     """JSON:API primary response object."""

#     class Config(BaseConfig):
#         """Mashumaro config for Resource."""

#         # Allows aliased type_ attribute to be used as discriminator.
#         discriminator = Discriminator(include_subtypes=True)


class JsonApiResponse(JsonApiBaseElement):
    """JSON:API primary response object."""

    class Config(BaseConfig):
        """Mashumaro config for Resource."""

        forbid_extra_keys = True
        discriminator = Discriminator(include_subtypes=True)


# @dataclass
# class SuccessResponse(JsonApiResponse, Generic[ResourceT]):
#     """
#     Represent a successful response in the JSON:API format.

#     A successful response includes the primary data (either a single resource or a list of resources), optional included resources, meta-information, links, and JSON:API details.
#     """

#     # fmt: off
#     data: ResourceT | list[ResourceT]
#     included:  list[BaseSupportedResource | UnsupportedResource] | None = None
#     meta: Meta | Meta | None = None
#     links: LinksModel | None = None
#     jsonapi: Jsonapi | None = None
#     # fmt: on


@dataclass
class SuccessResponse(JsonApiResponse):
    """
    Represent a successful response in the JSON:API format.

    A successful response includes the primary data (either a single resource or a list of resources), optional included resources, meta-information, links, and JSON:API details.
    """

    # fmt: off
    data: BaseSupportedResource | UnsupportedResource | list[BaseSupportedResource] | list[UnsupportedResource]
    included:  list[BaseSupportedResource | UnsupportedResource] | None = None
    meta: Meta | Meta | None = None
    links: LinksModel | None = None
    jsonapi: Jsonapi | None = None
    # fmt: on


@dataclass
class FailureResponse(JsonApiResponse):
    """
    Represent a failure response in the JSON:API format.

    A failure response typically contains a list of errors, meta-information, JSON:API object details, and links related to the error or failure.
    """

    errors: list[Error]
    meta: Meta | None = None
    jsonapi: Jsonapi | None = None
    links: Links | None = None


@dataclass
class InfoResponse(JsonApiResponse):
    """
    Represent informational data in the JSON:API format.

    This class can be used for responses that primarily convey meta-information and JSON:API details, possibly with additional links.
    """

    meta: Meta
    links: Links | None = None
    jsonapi: Jsonapi | None = None
