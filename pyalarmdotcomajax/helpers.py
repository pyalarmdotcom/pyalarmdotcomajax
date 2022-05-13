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
        return value in cls._value2member_map_

    @classmethod
    def list(cls) -> list:
        """Return list of all enum members."""

        def get_enum_value(enum_class: Enum) -> Any:
            """Mypy choked when this was expressed as a lambda."""
            return enum_class.value

        return list(map(get_enum_value, cls))


def extract_field_value(field: Tag) -> str | None:
    """Extract value from BeautifulSoup4 text, checkbox, and dropdown fields."""

    log.debug("Extracting field: %s", field)

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
        log.error(
            "Unable to extract field. Failed on field %s",
            field,
        )
        raise UnexpectedDataStructure from err

    return value
