"""Load responses from JSON files."""

from importlib import resources


def get_http_body_json(name: str) -> str:
    """Get server/client response/request body from JSON file."""

    return resources.read_text(__package__, f"{name}.json")


def get_http_body_html(name: str) -> str:
    """Get server/client response/request body from HTML file."""

    return resources.read_text(__package__, f"{name}.html")
