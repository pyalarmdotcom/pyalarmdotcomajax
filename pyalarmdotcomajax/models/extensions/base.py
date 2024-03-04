"""Extended settings for Alarm.com devices."""

from abc import ABC
from dataclasses import dataclass

from mashumaro import DataClassDictMixin


@dataclass
class ExtensionAttributes(ABC, DataClassDictMixin):
    """Attributes for extensions."""


@dataclass
class Extension(ABC, DataClassDictMixin):
    """Base class for extensions."""

    _attributes: ExtensionAttributes
    _description: str | None = None

    @property
    def description(self) -> str | None:
        """Describe extension purpose."""

        return self._description
