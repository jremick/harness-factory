"""Safe and deterministic HDP input/output helpers."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import yaml
from yaml import tokens as yaml_tokens

from .diagnostics import HdpInputError


class _DuplicateKeyError(ValueError):
    """Raised before a mapping can silently replace an earlier value."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


_MAX_DOCUMENT_BYTES = 1_048_576
_MAX_DOCUMENT_DEPTH = 64
_MAX_DOCUMENT_ITEMS = 100_000
_YAML_MERGE_TAG = "tag:yaml.org,2002:merge"


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> Dict[Any, Any]:
    result: Dict[Any, Any] = {}
    for key_node, value_node in node.value:
        if key_node.tag == _YAML_MERGE_TAG:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "YAML merge keys are not supported",
                key_node.start_mark,
            )
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"mapping keys must be strings, found {type(key).__name__}",
                key_node.start_mark,
            )
        try:
            duplicate = key in result
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _unique_json_object(pairs: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"found duplicate key {key!r}")
        result[key] = value
    return result


def _reject_yaml_references(raw: str) -> None:
    """Reject YAML graph features before construction can expand them."""

    depth = 0
    starts = (
        yaml_tokens.BlockMappingStartToken,
        yaml_tokens.BlockSequenceStartToken,
        yaml_tokens.FlowMappingStartToken,
        yaml_tokens.FlowSequenceStartToken,
    )
    ends = (
        yaml_tokens.BlockEndToken,
        yaml_tokens.FlowMappingEndToken,
        yaml_tokens.FlowSequenceEndToken,
    )
    for token in yaml.scan(raw, Loader=_UniqueKeyLoader):
        if isinstance(token, (yaml_tokens.AnchorToken, yaml_tokens.AliasToken)):
            raise yaml.YAMLError("YAML anchors and aliases are not supported")
        if isinstance(token, starts):
            depth += 1
            if depth > _MAX_DOCUMENT_DEPTH:
                raise yaml.YAMLError(
                    f"document nesting exceeds maximum depth {_MAX_DOCUMENT_DEPTH}"
                )
        elif isinstance(token, ends):
            depth -= 1


def _check_document_limits(value: Any) -> None:
    """Bound the parsed JSON-compatible tree before validation uses it."""

    item_count = 0
    frontier = [(value, 1)]
    while frontier:
        current, depth = frontier.pop()
        if depth > _MAX_DOCUMENT_DEPTH:
            raise HdpInputError(
                f"document nesting exceeds maximum depth {_MAX_DOCUMENT_DEPTH}"
            )
        if isinstance(current, dict):
            item_count += len(current)
            frontier.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            item_count += len(current)
            frontier.extend((item, depth + 1) for item in current)
        if item_count > _MAX_DOCUMENT_ITEMS:
            raise HdpInputError(
                f"document contains more than {_MAX_DOCUMENT_ITEMS} items"
            )


def load_document_bytes(
    raw_bytes: bytes, *, suffix: str, label: str
) -> Dict[str, Any]:
    """Parse a bounded JSON/YAML mapping already read through a trusted boundary."""

    if len(raw_bytes) > _MAX_DOCUMENT_BYTES:
        raise HdpInputError(
            f"cannot read {label}: document exceeds {_MAX_DOCUMENT_BYTES} bytes"
        )
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HdpInputError(f"cannot read {label}: document is not valid UTF-8") from exc

    try:
        if suffix.lower() == ".json":
            value = json.loads(raw, object_pairs_hook=_unique_json_object)
        elif suffix.lower() in {".yaml", ".yml"}:
            _reject_yaml_references(raw)
            value = yaml.load(raw, Loader=_UniqueKeyLoader)
        else:
            raise HdpInputError(
                f"unsupported document extension for {label}; expected .json, .yaml, or .yml"
            )
    except (json.JSONDecodeError, yaml.YAMLError, _DuplicateKeyError, RecursionError) as exc:
        raise HdpInputError(f"cannot parse {label}: {exc}") from exc

    if not isinstance(value, dict):
        raise HdpInputError(f"{label} must contain one top-level mapping/object")
    _check_document_limits(value)
    return value


def load_document(path: Path) -> Dict[str, Any]:
    """Load a JSON or YAML mapping without constructing arbitrary objects."""

    try:
        with path.open("rb") as stream:
            raw_bytes = stream.read(_MAX_DOCUMENT_BYTES + 1)
    except OSError as exc:
        raise HdpInputError(f"cannot read {path}: {exc}") from exc
    return load_document_bytes(raw_bytes, suffix=path.suffix, label=str(path))


def canonical_json(value: Any) -> str:
    """Serialize content for stable hashing and golden comparisons."""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def dump_json(value: Any, *, pretty: bool = True) -> str:
    if pretty:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return canonical_json(value) + "\n"


def dump_yaml(value: Any) -> str:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def atomic_write_text(path: Path, content: str, *, mode: int = 0o644) -> None:
    """Atomically replace a generated file without exposing partial content."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
