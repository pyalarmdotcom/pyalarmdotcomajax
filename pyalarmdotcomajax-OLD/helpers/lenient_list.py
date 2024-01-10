"""Pydantic core schema extension that ignore all list items that don't pass type validation."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, List, TypeVar

from pydantic_core import ValidationError
from pydantic_core import core_schema as cs

# https://github.com/pydantic/pydantic/issues/2274#issuecomment-1528052185

_ERROR = object()


@dataclass
class ErorrItemsMarker:
    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: Callable[[Any], cs.CoreSchema]
    ) -> cs.CoreSchema:
        schema = handler(source_type)

        def val(v: Any, handler: cs.ValidatorFunctionWrapHandler) -> Any:
            try:
                return handler(v)
            except ValidationError:
                return _ERROR

        return cs.no_info_wrap_validator_function(val, schema, serialization=schema.get("serialization"))


@dataclass
class ListErrorFilter:
    def __get_pydantic_core_schema__(
        self, source_type: Any, handler: Callable[[Any], cs.CoreSchema]
    ) -> cs.CoreSchema:
        schema = handler(source_type)

        def val(v: List[Any]) -> List[Any]:
            return [item for item in v if item is not _ERROR]

        return cs.no_info_after_validator_function(val, schema, serialization=schema.get("serialization"))


T = TypeVar("T")

LenientList = Annotated[List[Annotated[T, ErorrItemsMarker()]], ListErrorFilter()]
