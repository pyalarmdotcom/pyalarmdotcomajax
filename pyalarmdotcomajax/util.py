"""Generic helper functions."""

from __future__ import annotations

import contextlib
import logging
from enum import Enum
from typing import Any

from bs4 import Tag

from pyalarmdotcomajax.models.jsonapi import Resource, ResourceIdentifier

log = logging.getLogger(__name__)


class EnumDictMixin(Enum):
    """Outputs the value of the enum when used within a dict."""

    def __str__(self) -> str:
        """Return the value of the enum."""
        return str(self.value)


def get_related_entity_id_by_key(resource: Resource, name: str) -> str | None:
    """Return related entity ID by relationship dict key."""

    with contextlib.suppress(Exception):
        if isinstance(relation_id := resource.relationships[name].data["id"], str):  # type: ignore
            return relation_id

    return None


def get_all_related_entity_ids(resource: Resource) -> set[str]:
    """Return related entity ID by relationship dict key."""

    relations = set({})

    rel_items = resource.relationships or {}

    for rel_value in rel_items.values():
        if hasattr(rel_value, "data"):
            if isinstance(rel_value.data, ResourceIdentifier):
                relations.add(rel_value.data.id)
            if isinstance(rel_value.data, list):
                for item in rel_value.data:
                    if isinstance(item, dict):
                        relations.add(item["id"])

    return relations


def extract_field_value(field: Tag) -> str:
    """Extract value from BeautifulSoup4 text, checkbox, and dropdown fields."""

    # log.debug("Extracting field: %s", field)

    value = None

    try:
        if field.attrs.get("name") and field.name == "select":
            value = field.findChild(attrs={"selected": "selected"}).attrs["value"]
        elif field.attrs.get("checked") and field.attrs.get("checked"):
            value = field.attrs["checked"] == "checked"
        elif field.attrs.get("value"):
            value = field.attrs["value"]

    except (KeyError, AttributeError) as err:
        raise ValueError from err

    if not value:
        raise ValueError("Value not found.")

    return str(value)


# def slug_to_title(slug: str) -> str:
#     """Convert slug to title case."""

#     return slug.replace("_", " ").title()


# https://stackoverflow.com/a/39542816/20207204
class classproperty(property):
    """Decorator for class properties. Allows class functions to be used as properties."""

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        """Get the value of the property."""
        return super().__get__(objtype)

    def __set__(self, obj: Any, value: Any) -> None:
        """Set the value of the property."""
        super().__set__(type(obj), value)

    def __delete__(self, obj: Any) -> None:
        """Delete the value of the property."""
        super().__delete__(type(obj))
