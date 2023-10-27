"""Sphinx configuration."""

import os
import sys

try:
    from pyalarmdotcomajax._version import version as release
except ImportError:
    release = "unknown"

sys.path.insert(0, os.path.abspath(".."))

version = release.split("+")[0]  # Optional: trim off dev metadata
autodoc_default_options = {
    "members": True,
    "undoc-members": False,  # Hides undocumented methods
    "private-members": False,  # Hides _private methods
    "show-inheritance": True,
}
autodoc_mock_imports = ["mashumaro", "pyalarmdotcomajax.models.jsonapi"]
project = "pyalarmdotcomajax"
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
html_theme = "furo"
autodoc_typehints = "description"
autodoc_typehints_format = "short"  # avoids fully-qualified names

exclude_patterns = [
    "api/pyalarmdotcomajax.adc.rst",
    "api/_autosummary/pyalarmdotcomajax.adc.*",
]
