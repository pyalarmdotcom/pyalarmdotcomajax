"""Generic helper functions."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import asdict
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar, overload

from tabulate import tabulate
from termcolor import colored

from pyalarmdotcomajax.models.jsonapi import Resource, ResourceIdentifier

if TYPE_CHECKING:
    from pyalarmdotcomajax.models.base import AdcResource

log = logging.getLogger(__name__)


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
                    if isinstance(item, ResourceIdentifier):
                        relations.add(item.id)

    return relations


def slug_to_title(slug: str) -> str:
    """Convert slug to title case."""

    return slug.replace("_", " ").title()


T = TypeVar("T")


@overload
def cli_format(value: bool | Enum) -> str: ...


@overload
def cli_format(value: Any) -> Any: ...


def cli_format(value: T | Any) -> T | str:
    """Format value for CLI output."""

    # Change Value

    if isinstance(value, Enum):
        value = value.name.title()

    if value is True:
        value = "√"

    if value is False:
        value = "X"

    # Truncate

    if isinstance(value, str) and len(value) > 100:
        value = value[:100] + "..."

    # Color

    if value in ["√", "Closed", "Locked", "Armed Stay", "Armed Night", "Armed Away", "On"]:
        value = colored(str(value), "green")

    if value in ["X", "Open", "Unlocked", "Disarmed", "Off"]:
        value = colored(str(value), "red")

    return value


def resources_pretty_str(resource_type_str: str, resources: list[AdcResource]) -> str:
    """Return string representation of resources in controller."""

    response = (
        "\n\n"
        + colored(
            f"====[ {slug_to_title(resource_type_str)} ]====",
            "grey",
            "on_yellow",
            attrs=["bold"],
        )
        + "\n\n"
    )

    if len(resources) == 0:
        return str(response + tabulate([["None"]], tablefmt="mixed_grid"))

    table_data = []
    for resource in resources:
        table_row = [resource.id]

        if description := getattr(resource.attributes, "description", None):
            table_row.append(colored(description, attrs=["bold"]))

        if state := getattr(resource.attributes, "state", None):
            table_row.append(cli_format(state))

        table_data.append(
            [
                *table_row,
                *(
                    [
                        cli_format(value)
                        for key, value in asdict(resource.attributes).items()
                        if key not in ["description", "state"]
                    ]
                ),
            ]
        )

    headers = ["ID"]

    if description := getattr(resource.attributes, "description", None):
        headers.append(colored("Name", attrs=["bold"]))

    if state := getattr(resource.attributes, "state", None):
        headers.append("State")

    headers.extend([slug_to_title(k) for k in asdict(resource.attributes) if k not in ["description", "state"]])

    return str(response + tabulate(table_data, headers, tablefmt="mixed_grid"))


def resources_raw_str(resource_type_str: str, resources: list[Resource | AdcResource]) -> str:
    """Return raw JSON for all controller resources."""

    header = (
        "\n"
        + colored(
            f"====[ {slug_to_title(resource_type_str)} ]====",
            "grey",
            "on_yellow",
            attrs=["bold"],
        )
        + "\n\n"
    )

    if len(resources) == 0:
        return str(header + "(None)\n\n")

    body = ""
    for resource in resources:
        body += (
            colored(
                resource.attributes.get("description", "Unnamed Resource").upper()
                if isinstance(resource, Resource)
                else getattr(
                    resource.attributes, "description", f"Unnamed {slug_to_title(resource_type_str)}"
                ).upper(),
                attrs=["bold", "underline"],
            )
            + ": "
            + str(resource.to_dict() if isinstance(resource, Resource) else resource.api_resource.to_dict())
            + "\n\n"
        )

    return str(header + body)
