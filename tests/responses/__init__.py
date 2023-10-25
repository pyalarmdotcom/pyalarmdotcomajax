"""Load responses from JSON files."""

from importlib import resources


def get_http_body_json(name: str) -> str:
    """Get server/client response/request body from JSON file."""

    return resources.files(__package__).joinpath(f"{name}.json").read_text()


def get_http_body_html(name: str) -> str:
    """Get server/client response/request body from HTML file."""

    return resources.files(__package__).joinpath(f"{name}.html").read_text()
