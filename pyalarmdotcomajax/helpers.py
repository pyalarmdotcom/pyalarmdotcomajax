"""Generic helper functions."""
from __future__ import annotations

from enum import Enum
import logging
from typing import Any

from bs4 import Tag
from pyalarmdotcomajax.errors import UnexpectedDataStructure

log = logging.getLogger(__name__)


class ExtendedEnumMixin(Enum):
    """Search and export-list functions to enums."""

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Return whether value exists in enum."""

        return str(value).upper() in [
            str(item).upper() for item in cls._value2member_map_
        ]

    @classmethod
    def has_key_(cls, key: str) -> Any:
        """Return whether value exists in enum."""

        return str(key).upper() in [str(item).upper() for item in cls._member_names_]

    @classmethod
    def enum_from_key(cls, key: str) -> Any:
        """Return enum from key name."""

        return_member = None

        for member_name, member in cls._member_map_.items():
            if str(key).upper() == str(member_name).upper():
                return_member = member
                break

        if not return_member:
            raise ValueError("Member not found.")

        return return_member

    @classmethod
    def values(cls) -> list:
        """Return list of all enum members."""

        return [key for key, _ in cls._value2member_map_]

    @classmethod
    def names(cls) -> list[str]:
        """Return list of all enum members."""

        return cls._member_names_


def extract_field_value(field: Tag) -> str | None:
    """Extract value from BeautifulSoup4 text, checkbox, and dropdown fields."""

    # log.debug("Extracting field: %s", field)

    value: str | None = None
    try:
        if field.attrs.get("name") and field.name == "select":
            value = field.findChild(attrs={"selected": "selected"}).attrs["value"]
        elif field.attrs.get("checked") and (is_checked := field.attrs["checked"]):
            value = is_checked == "checked"
        elif field.attrs.get("value"):
            value = field.attrs["value"]
        else:
            pass

    except (KeyError, AttributeError) as err:
        raise UnexpectedDataStructure from err

    return value


def slug_to_title(slug: str) -> str:
    """Convert slug to title case."""

    return slug.replace("_", " ").title()
