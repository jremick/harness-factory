"""Draft 2020-12 structural validation for HDP documents."""

from importlib import resources
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .diagnostics import Diagnostic, HdpInputError
from .io import load_document


JsonPathPart = Union[str, int]


def canonical_schema_path() -> Path:
    resource = resources.files("hdp").joinpath("schemas", "hdp.schema.json")
    return Path(str(resource))


def _pointer(parts: Iterable[JsonPathPart]) -> str:
    encoded = []
    for part in parts:
        text = str(part).replace("~", "~0").replace("/", "~1")
        encoded.append(text)
    return "" if not encoded else "/" + "/".join(encoded)


def load_canonical_schema() -> Dict[str, Any]:
    path = canonical_schema_path()
    if not path.exists():
        raise HdpInputError(f"canonical schema is not installed at {path}")
    schema = load_document(path)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise HdpInputError(f"canonical schema is invalid: {exc.message}") from exc
    return schema


def structural_diagnostics(instance: Dict[str, Any]) -> List[Diagnostic]:
    schema = load_canonical_schema()
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            tuple(str(part) for part in error.absolute_schema_path),
            error.message,
        ),
    )
    return [
        Diagnostic(
            code="HDP-STRUCTURE",
            message=error.message,
            instance_path=_pointer(error.absolute_path),
            rule_id=_pointer(error.absolute_schema_path),
        )
        for error in errors
    ]

