"""Generic helper functions."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from bs4 import Tag

log = logging.getLogger(__name__)


class CastingMixin:
    """Functions used for pulling data from JSON in standardized format."""

    def _safe_int_from_dict(self, src_dict: dict, key: str) -> int | None:
        """Cast raw value to int. Satisfies mypy."""

        try:
            return int(src_dict.get(key))  # type: ignore
        except (ValueError, TypeError):
            return None

    def _safe_float_from_dict(self, src_dict: dict, key: str) -> float | None:
        """Cast raw value to int. Satisfies mypy."""

        try:
            return float(src_dict.get(key))  # type: ignore
        except (ValueError, TypeError):
            return None

    def _safe_str_from_dict(self, src_dict: dict, key: str) -> str | None:
        """Cast raw value to str. Satisfies mypy."""

        try:
            return str(src_dict.get(key))
        except (ValueError, TypeError):
            return None

    def _safe_bool_from_dict(self, src_dict: dict, key: str) -> bool | None:
        """Cast raw value to bool. Satisfies mypy."""

        if src_dict.get(key) in [True, False]:
            return src_dict.get(key)

        return None

    def _safe_list_from_dict(self, src_dict: dict, key: str, value_type: type) -> list | None:
        """Cast raw value to list. Satisfies mypy."""

        try:
            extracted_list: list = list(src_dict.get(key))  # type: ignore
            for duration in extracted_list:
                value_type(duration)
        except (ValueError, TypeError):
            pass
        else:
            return extracted_list

        return None

    def _safe_special_from_dict(self, src_dict: dict, key: str, value_type: type) -> Any | None:
        """Cast raw value to specified type. Satisfies mypy."""

        try:
            return value_type(src_dict.get(key))
        except (ValueError, TypeError):
            pass

        return None


class ExtendedEnumMixin(Enum):
    """Search and export-list functions to enums."""

    @classmethod
    def has_value(cls, value: str) -> bool:
        """Return whether value exists in enum."""

        return str(value).upper() in [str(item).upper() for item in cls._value2member_map_]

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


def slug_to_title(slug: str) -> str:
    """Convert slug to title case."""

    return slug.replace("_", " ").title()


# https://stackoverflow.com/a/39542816/20207204
class classproperty(property):
    """Decorator for class properties. Lets class functions to be used as properties."""

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        """Get the value of the property."""
        return super().__get__(objtype)

    def __set__(self, obj: Any, value: Any) -> None:
        """Set the value of the property."""
        super().__set__(type(obj), value)

    def __delete__(self, obj: Any) -> None:
        """Delete the value of the property."""
        super().__delete__(type(obj))
