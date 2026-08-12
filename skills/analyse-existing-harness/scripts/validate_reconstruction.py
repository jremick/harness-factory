#!/usr/bin/env python3
"""Validate HDP structure, semantics, evidence, and assessment fidelity."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from reconstruction_semantics import semantic_messages


RECONSTRUCTION_KEY = "x-hdp-reconstruction"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
LINE_LOCATION = re.compile(r"^lines?\s+(\d+)(?:\s*-\s*(\d+))?$", re.IGNORECASE)


class _DuplicateKeyError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
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


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"found duplicate key {key!r}")
        result[key] = value
    return result


def load_document(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw, object_pairs_hook=_unique_json_object)
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.load(raw, Loader=_UniqueKeyLoader)
    raise ValueError(f"unsupported document extension for {path}")


def _escape(token: Any) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def leaves(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            if path == "/extensions" and key == RECONSTRUCTION_KEY:
                continue
            yield from leaves(value[key], f"{path}/{_escape(key)}")
    elif isinstance(value, list):
        if not value:
            yield path, value
        for index, item in enumerate(value):
            yield from leaves(item, f"{path}/{index}")
    else:
        yield path, value


def resolve_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("must be an RFC 6901 JSON Pointer beginning with '/'")
    current = document
    for raw_token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw_token):
            raise ValueError(f"invalid JSON Pointer escape in token {raw_token!r}")
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(token)
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise KeyError(token)
            index = int(token)
            if index >= len(current):
                raise IndexError(index)
            current = current[index]
        else:
            raise KeyError(token)
    return current


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def _safe_source_path(source: Any) -> str | None:
    if not isinstance(source, str) or not source:
        return None
    candidate = Path(source)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    normalized = candidate.as_posix()
    if normalized in {"", "."}:
        return None
    return normalized


def _inventory_index(
    inventory: Any, label: str, messages: list[str]
) -> dict[str, dict[str, Any]]:
    if not isinstance(inventory, dict) or not isinstance(inventory.get("files"), list):
        messages.append(f"inventory {label}: must contain a files array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(inventory["files"]):
        if not isinstance(item, dict):
            messages.append(f"inventory {label} /files/{index}: must be a mapping")
            continue
        source = _safe_source_path(item.get("path"))
        if source is None:
            messages.append(f"inventory {label} /files/{index}/path: invalid relative path")
            continue
        if source in result:
            messages.append(f"inventory {label} /files/{index}/path: duplicate path {source!r}")
            continue
        result[source] = item
    return result


def _location_messages(source_path: Path, location: Any, label: str) -> list[str]:
    if not isinstance(location, str) or not location.strip():
        return [f"evidence {label}: location must be a non-empty string"]
    location = location.strip()
    line_match = LINE_LOCATION.fullmatch(location)
    if line_match:
        try:
            line_count = len(source_path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError) as exc:
            return [f"evidence {label}: cannot verify line location: {exc}"]
        start = int(line_match.group(1))
        end = int(line_match.group(2) or start)
        if start < 1 or end < start or end > line_count:
            return [
                f"evidence {label}: line location {location!r} is outside 1-{line_count}"
            ]
        return []

    pointers = [part.strip() for part in location.split(" and ")]
    if all(part.startswith("/") for part in pointers):
        if source_path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            return [f"evidence {label}: JSON Pointer location requires JSON or YAML source"]
        try:
            source_document = load_document(source_path)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            return [f"evidence {label}: cannot parse source for location: {exc}"]
        errors: list[str] = []
        for pointer in pointers:
            try:
                resolve_pointer(source_document, pointer)
            except (ValueError, KeyError, IndexError) as exc:
                errors.append(f"evidence {label}: location {pointer!r} does not resolve: {exc}")
        return errors

    key_match = re.fullmatch(r"key\s+(.+)", location, flags=re.IGNORECASE)
    if key_match:
        try:
            document = load_document(source_path)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            return [f"evidence {label}: cannot parse source for key location: {exc}"]
        key = key_match.group(1).strip()

        def contains(value: Any) -> bool:
            if isinstance(value, dict):
                return key in value or any(contains(item) for item in value.values())
            if isinstance(value, list):
                return any(contains(item) for item in value)
            return False

        if not contains(document):
            return [f"evidence {label}: key {key!r} does not resolve"]
        return []
    return [
        f"evidence {label}: unsupported location {location!r}; use JSON Pointer, key NAME, or line range"
    ]


def evidence_messages(
    assessments: list[Any],
    reconstruction: dict[str, Any],
    inventory_path: Path | None,
    root: Path | None,
) -> list[str]:
    messages: list[str] = []
    inventory: Any = None
    inventory_label = "embedded"
    if inventory_path is not None:
        inventory_label = str(inventory_path)
        try:
            inventory = load_document(inventory_path)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            return [f"inventory {inventory_path}: cannot load: {exc}"]
        expected_digest = reconstruction.get("inventorySha256")
        actual_digest = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
        if expected_digest is not None and expected_digest != actual_digest:
            messages.append(
                f"inventory {inventory_path}: sha256 {actual_digest} does not match reconstruction inventorySha256 {expected_digest!r}"
            )
        embedded = reconstruction.get("inventory")
        if embedded is not None and embedded != inventory.get("files"):
            messages.append(f"inventory {inventory_path}: files differ from embedded inventory")
    elif isinstance(reconstruction.get("inventory"), list):
        inventory = {"files": reconstruction["inventory"]}

    inventory_by_source = (
        _inventory_index(inventory, inventory_label, messages) if inventory is not None else {}
    )

    if root is None and isinstance(inventory, dict) and isinstance(inventory.get("root"), str):
        root = Path(inventory["root"])
    resolved_root = root.resolve() if root is not None else None
    if resolved_root is not None and not resolved_root.is_dir():
        messages.append(f"evidence root {resolved_root}: not a directory")
        resolved_root = None

    for assessment_index, assessment in enumerate(assessments):
        if not isinstance(assessment, dict):
            continue
        for evidence_index, evidence in enumerate(assessment.get("evidence", [])):
            label = f"{assessment.get('path')!r} item {evidence_index}"
            if not isinstance(evidence, dict):
                messages.append(f"evidence {label}: must be a mapping")
                continue
            source = _safe_source_path(evidence.get("source"))
            digest = evidence.get("sha256")
            if source is None:
                messages.append(f"evidence {label}: source must be a safe relative path")
                continue
            if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
                messages.append(f"evidence {label}: sha256 must be 64 lowercase hexadecimal characters")
                continue
            if inventory is not None:
                inventory_item = inventory_by_source.get(source)
                if inventory_item is None:
                    messages.append(f"evidence {label}: source {source!r} is absent from inventory")
                elif inventory_item.get("sha256") != digest:
                    messages.append(
                        f"evidence {label}: sha256 does not match inventory for {source!r}"
                    )
            if resolved_root is not None:
                source_path = (resolved_root / source).resolve()
                if not source_path.is_relative_to(resolved_root):
                    messages.append(f"evidence {label}: source escapes evidence root")
                    continue
                if not source_path.is_file():
                    messages.append(f"evidence {label}: source does not exist under evidence root")
                    continue
                actual_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
                if actual_digest != digest:
                    messages.append(
                        f"evidence {label}: sha256 {digest} does not match source digest {actual_digest}"
                    )
                messages.extend(_location_messages(source_path, evidence.get("location"), label))
    return messages


def validate_assessments(
    definition: dict[str, Any],
    reconstruction: dict[str, Any],
    *,
    accepted_absent_paths: set[str] | None = None,
) -> tuple[list[str], list[Any], int]:
    messages: list[str] = []
    assessments = reconstruction.get("fieldAssessments", [])
    if not isinstance(assessments, list):
        return ["assessment /extensions/x-hdp-reconstruction/fieldAssessments: must be an array"], [], 0

    expected = dict(leaves(definition))
    expected.update({path: None for path in accepted_absent_paths or set()})
    paths = [item.get("path") if isinstance(item, dict) else None for item in assessments]
    path_counts = Counter(path for path in paths if isinstance(path, str))
    for path, count in sorted(path_counts.items()):
        if count > 1:
            messages.append(f"assessment {path}: duplicate ({count} entries)")

    valid_paths = set(path_counts)
    for path in sorted(set(expected) - valid_paths):
        messages.append(f"assessment {path}: missing")
    for path in sorted(valid_paths - set(expected)):
        try:
            resolve_pointer(definition, path)
        except (ValueError, KeyError, IndexError) as exc:
            messages.append(f"assessment {path}: pointer does not resolve: {exc}")
        else:
            messages.append(f"assessment {path}: extra; pointer is not an HDP leaf")

    for index, item in enumerate(assessments):
        if not isinstance(item, dict):
            messages.append(f"assessment index {index}: must be a mapping")
            continue
        path = item.get("path")
        if not isinstance(path, str):
            messages.append(f"assessment index {index}: path must be a string")
            continue
        try:
            actual_value = resolve_pointer(definition, path)
        except (ValueError, KeyError, IndexError):
            actual_value = None
        if "value" not in item:
            messages.append(f"assessment {path}: value is missing")
        elif path in expected and not _same_value(item["value"], actual_value):
            messages.append(f"assessment {path}: value does not match HDP value")

        status = item.get("epistemicStatus")
        confidence = item.get("confidence")
        if item.get("claimClass") not in {
            "evidenced-intended-outcome",
            "operational-behavior",
            "inferred-intent",
            "administrative-metadata",
            "absent-or-unknowable",
        }:
            messages.append(f"assessment {path}: invalid claimClass")
        if status not in {"observed", "declared", "inferred", "unknown"}:
            messages.append(f"assessment {path}: invalid epistemicStatus")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            messages.append(f"assessment {path}: confidence must be between 0 and 1")
        if status == "unknown" and confidence != 0:
            messages.append(f"assessment {path}: unknown must use confidence 0")
        if status == "inferred" and isinstance(confidence, (int, float)) and confidence >= 0.8:
            messages.append(f"assessment {path}: inferred confidence must be below 0.8")
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            messages.append(f"assessment {path}: evidence must be an array")
            evidence = []
        if status in {"observed", "declared"} and not evidence:
            messages.append(f"assessment {path}: {status} requires evidence")
        if status in {"inferred", "unknown"} and item.get("humanConfirmationRequired") is not True:
            messages.append(f"assessment {path}: {status} requires human confirmation")
    return messages, assessments, len(expected)


_PUBLIC_PROJECTION_OMISSIONS = {
    "datasets": {"name", "version"},
    "fixtures": {"name"},
    "tests": {"name", "type", "expected"},
}


def accepted_public_projection_unknowns(
    definition: dict[str, Any], reconstruction: dict[str, Any]
) -> set[str]:
    """Recognise only analyser-authored unknowns for redacted hidden fields."""

    if (
        reconstruction.get("generationReady") is not False
        or reconstruction.get("sourceMode") != "embedded-generated-public-projection"
        or not isinstance(reconstruction.get("evidenceMap"), str)
    ):
        return set()
    evaluation = definition.get("evaluation")
    assessments = reconstruction.get("fieldAssessments")
    if not isinstance(evaluation, dict) or not isinstance(assessments, list):
        return set()

    accepted: set[str] = set()
    for item in assessments:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        match = re.fullmatch(
            r"/evaluation/(datasets|fixtures|tests)/(0|[1-9][0-9]*)/([^/]+)",
            path if isinstance(path, str) else "",
        )
        if match is None:
            continue
        collection, raw_index, field = match.groups()
        if field not in _PUBLIC_PROJECTION_OMISSIONS[collection]:
            continue
        records = evaluation.get(collection)
        index = int(raw_index)
        if (
            not isinstance(records, list)
            or index >= len(records)
            or not isinstance(records[index], dict)
            or records[index].get("visibility") != "hidden"
            or field in records[index]
        ):
            continue
        expected_reason = (
            f"The public projection intentionally omits hidden evaluator field {field!r}."
        )
        if (
            item.get("value") is None
            and item.get("claimClass") == "absent-or-unknowable"
            and item.get("epistemicStatus") == "unknown"
            and item.get("confidence") == 0
            and item.get("evidence") == []
            and item.get("contradictions") == []
            and item.get("missingEvidence") == [expected_reason]
            and item.get("humanConfirmationRequired") is True
        ):
            accepted.add(path)
    return accepted


def required_error_is_accepted(error: Any, accepted_absent_paths: set[str]) -> bool:
    """Suppress only required-property errors covered by accepted redaction records."""

    if error.validator != "required" or not isinstance(error.instance, dict):
        return False
    missing = [
        item for item in error.validator_value
        if isinstance(item, str) and item not in error.instance
    ] if isinstance(error.validator_value, list) else []
    base = "".join(f"/{_escape(item)}" for item in error.absolute_path)
    paths = {f"{base}/{_escape(item)}" for item in missing}
    return bool(paths) and paths <= accepted_absent_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hdp", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "hdp.schema.json",
    )
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--root", "--harness-root", dest="root", type=Path)
    args = parser.parse_args()

    try:
        definition = load_document(args.hdp)
        schema = load_document(args.schema)
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print("ERROR", f"input: {exc}")
        return 2
    if not isinstance(definition, dict) or not isinstance(schema, dict):
        print("ERROR input: HDP and schema must be mappings")
        return 2

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(definition),
        key=lambda item: (list(item.path), item.message),
    )
    messages: list[str] = []
    extensions = definition.get("extensions", {})
    reconstruction = (
        extensions.get(RECONSTRUCTION_KEY, {}) if isinstance(extensions, dict) else {}
    )
    if not isinstance(reconstruction, dict):
        reconstruction = {}
        messages.append(f"assessment /extensions/{RECONSTRUCTION_KEY}: missing or invalid")
    embedded_reconstruction = reconstruction

    # The canonical contract keeps field evidence in an adjacent evidence map,
    # not inside the HDP extension. Adapt its stable record shape to this
    # validator's internal assessment representation.
    evidence_ref = reconstruction.get("evidenceMap")
    evidence_path = Path(evidence_ref) if isinstance(evidence_ref, str) else None
    if evidence_path is not None and not evidence_path.is_absolute():
        evidence_path = args.hdp.resolve().parent / evidence_path
    try:
        evidence_map = load_document(evidence_path) if evidence_path else {}
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        messages.append(f"evidence-map: cannot read declared evidence map: {exc}")
        evidence_map = {}
    records = evidence_map.get("records", []) if isinstance(evidence_map, dict) else []
    assessments = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            assessments.append(record)
            continue
        sources = []
        for source in record.get("sources", []):
            if not isinstance(source, dict):
                sources.append(source)
                continue
            digest = source.get("digest", "")
            sources.append({
                "source": source.get("path"),
                "location": source.get("location"),
                "sha256": digest.removeprefix("sha256:") if isinstance(digest, str) else digest,
            })
        confirmation = record.get("humanConfirmation", {})
        assessments.append({
            "path": record.get("field"),
            "value": record.get("value"),
            "claimClass": record.get("claimClass"),
            "epistemicStatus": record.get("epistemicStatus"),
            "confidence": record.get("confidence"),
            "evidence": sources,
            "contradictions": record.get("contradictions", []),
            "missingEvidence": record.get("missingEvidence", []),
            "humanConfirmationRequired": (
                confirmation.get("required") if isinstance(confirmation, dict) else False
            ),
        })
    reconstruction = {**reconstruction, "fieldAssessments": assessments}
    if not isinstance(evidence_ref, str):
        # Backward-compatible input used by v0 skill fixtures. New analyser
        # output uses the adjacent evidence map above.
        reconstruction = embedded_reconstruction

    accepted_absent_paths = accepted_public_projection_unknowns(
        definition, reconstruction
    )
    remaining_errors = [
        item for item in errors
        if not required_error_is_accepted(item, accepted_absent_paths)
    ]
    messages.extend(
        f"structure /{'/'.join(map(str, item.path))}: {item.message}"
        for item in remaining_errors
    )
    assessment_messages, assessments, expected_count = validate_assessments(
        definition, reconstruction, accepted_absent_paths=accepted_absent_paths
    )
    messages.extend(assessment_messages)
    if not remaining_errors:
        messages.extend(semantic_messages(definition))
    messages.extend(
        evidence_messages(assessments, reconstruction, args.inventory, args.root)
    )
    if reconstruction.get("generationReady") and any(
        isinstance(item, dict) and item.get("epistemicStatus") == "unknown"
        for item in assessments
    ):
        messages.append("readiness: generationReady cannot be true while unknown fields remain")

    if messages:
        for message in sorted(set(messages)):
            print("ERROR", message)
        return 2
    print(f"VALID {args.hdp} ({expected_count} assessed leaf fields)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
