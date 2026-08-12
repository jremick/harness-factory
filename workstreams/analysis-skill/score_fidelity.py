#!/usr/bin/env python3
"""Deterministically score an HDP reconstruction against evaluator-private facts.

The reconstruction agent must not receive the expected manifest or this script's
results. JSON is always supported. YAML support uses PyYAML when available.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


MISSING = object()


def load_document(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw)
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("PyYAML is required to score YAML input") from exc
        return yaml.safe_load(raw)
    raise ValueError(f"unsupported file extension: {path}")


def decode_pointer_part(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def resolve_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError(f"not an RFC 6901 pointer: {pointer}")
    current = document
    for raw_part in pointer[1:].split("/"):
        part = decode_pointer_part(raw_part)
        if isinstance(current, Mapping):
            if part not in current:
                return MISSING
            current = current[part]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            try:
                index = int(part)
            except ValueError:
                return MISSING
            if index < 0 or index >= len(current):
                return MISSING
            current = current[index]
        else:
            return MISSING
    return current


def remove_pointer(document: Any, pointer: str) -> None:
    if pointer == "":
        raise ValueError("cannot remove the document root")
    if not pointer.startswith("/"):
        raise ValueError(f"not an RFC 6901 pointer: {pointer}")
    parts = [decode_pointer_part(part) for part in pointer[1:].split("/")]
    current = document
    for part in parts[:-1]:
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return
        else:
            return
    final = parts[-1]
    if isinstance(current, dict):
        current.pop(final, None)
    elif isinstance(current, list):
        try:
            del current[int(final)]
        except (ValueError, IndexError):
            return


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def normalize_text(value: Any, *, casefold: bool = False) -> Any:
    if not isinstance(value, str):
        return value
    result = " ".join(unicodedata.normalize("NFC", value).split())
    return result.casefold() if casefold else result


def semantic_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: semantic_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        normalized = [semantic_json(item) for item in value]
        if all(isinstance(item, Mapping) and isinstance(item.get("id"), str) for item in normalized):
            return sorted(normalized, key=lambda item: str(item["id"]))
        if all(not isinstance(item, (Mapping, list)) for item in normalized):
            return sorted(normalized, key=canonical)
        return normalized
    return value


def strings_in(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_in(item)


def normalize(value: Any, normalizer: str) -> Any:
    if normalizer == "exact":
        return value
    if normalizer == "text":
        return normalize_text(value)
    if normalizer == "casefold-text":
        return normalize_text(value, casefold=True)
    if normalizer == "path":
        result = normalize_text(value)
        if not isinstance(result, str):
            return result
        result = result.replace("\\", "/")
        return result[2:] if result.startswith("./") else result
    if normalizer == "unordered-scalars":
        if not isinstance(value, list) or any(isinstance(item, (Mapping, list)) for item in value):
            return value
        return sorted(value, key=canonical)
    if normalizer == "semantic-json":
        return semantic_json(value)
    raise ValueError(f"unknown normalizer: {normalizer}")


def bounded_score_for_band(value: Any, band: Sequence[float]) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return 0.0
    low, high = float(band[0]), float(band[1])
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - (distance * 2.0))


def group_for_path(path: str, groups: Sequence[Mapping[str, Any]]) -> str | None:
    for group in groups:
        for prefix in group["prefixes"]:
            if path == prefix or path.startswith(prefix + "/"):
                return str(group["id"])
    return None


def source_path_matches(source: Mapping[str, Any], expected_paths: Sequence[str]) -> bool:
    actual = source.get("path") or source.get("uri")
    if not isinstance(actual, str):
        return False
    normalized_actual = actual.replace("\\", "/").removeprefix("./")
    return any(
        normalized_actual == expected.replace("\\", "/").removeprefix("./")
        or normalized_actual.endswith("/" + expected.replace("\\", "/").removeprefix("./"))
        for expected in expected_paths
    )


def normalize_evidence_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Accept the standalone ledger contract and the skill's embedded assessment shape."""

    normalized = dict(record)
    if "field" not in normalized and isinstance(normalized.get("path"), str):
        normalized["field"] = normalized["path"]
    if "sources" not in normalized and isinstance(normalized.get("evidence"), list):
        normalized["sources"] = [
            {
                **dict(item),
                **({"path": item["source"]} if isinstance(item, Mapping) and "source" in item and "path" not in item else {}),
            }
            if isinstance(item, Mapping)
            else item
            for item in normalized["evidence"]
        ]
    if "humanConfirmation" not in normalized and isinstance(
        normalized.get("humanConfirmationRequired"), bool
    ):
        required = normalized["humanConfirmationRequired"]
        normalized["humanConfirmation"] = {
            "required": required,
            "reason": (
                "Human confirmation is required by the reconstruction assessment."
                if required
                else ""
            ),
        }
    return normalized


def extract_evidence_records(ledger: Any, actual_hdp: Any) -> List[Dict[str, Any]]:
    candidates: Any = None
    if isinstance(ledger, Mapping):
        if isinstance(ledger.get("records"), list):
            candidates = ledger["records"]
        elif isinstance(ledger.get("fieldAssessments"), list):
            candidates = ledger["fieldAssessments"]
    if candidates is None and isinstance(actual_hdp, Mapping):
        candidates = (
            actual_hdp.get("extensions", {})
            .get("x-hdp-reconstruction", {})
            .get("fieldAssessments", [])
        )
    return [normalize_evidence_record(item) for item in candidates or [] if isinstance(item, Mapping)]


def validate_record_shape(record: Any, rubric: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    passed: List[str] = []
    failed: List[str] = []
    if not isinstance(record, Mapping):
        return passed, ["record-present"]
    passed.append("record-present")
    for field in rubric["requiredEvidenceRecordFields"]:
        (passed if field in record else failed).append(f"field:{field}")
    if record.get("claimClass") in rubric["allowedClaimClasses"]:
        passed.append("claim-class")
    else:
        failed.append("claim-class")
    if record.get("epistemicStatus") in rubric["confidenceBands"]:
        passed.append("epistemic-status")
    else:
        failed.append("epistemic-status")
    confidence = record.get("confidence")
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool) and 0 <= confidence <= 1:
        passed.append("confidence-range")
    else:
        failed.append("confidence-range")
    for array_field in ("sources", "contradictions", "missingEvidence"):
        if isinstance(record.get(array_field), list):
            passed.append(f"array:{array_field}")
        else:
            failed.append(f"array:{array_field}")
    confirmation = record.get("humanConfirmation")
    if (
        isinstance(confirmation, Mapping)
        and isinstance(confirmation.get("required"), bool)
        and isinstance(confirmation.get("reason"), str)
        and (not confirmation["required"] or bool(confirmation["reason"].strip()))
    ):
        passed.append("human-confirmation-shape")
    else:
        failed.append("human-confirmation-shape")
    return passed, failed


def schema_validation(instance: Any, schema: Any) -> Dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker  # type: ignore
    except ImportError:
        return {"status": "not-run", "reason": "jsonschema is not installed", "errors": []}
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (tuple(str(part) for part in error.absolute_path), error.message),
    )
    formatted = []
    for error in errors:
        pointer = "" if not error.absolute_path else "/" + "/".join(
            str(part).replace("~", "~0").replace("/", "~1") for part in error.absolute_path
        )
        formatted.append({"path": pointer, "message": error.message})
    return {"status": "pass" if not errors else "fail", "errors": formatted}


def classify_fact(
    fact: Mapping[str, Any],
    actual_hdp: Any,
    record: Any,
    rubric: Mapping[str, Any],
) -> Dict[str, Any]:
    path = str(fact["path"])
    actual_value = resolve_pointer(actual_hdp, path)
    expected_unknown = bool(fact.get("expectedUnknown", False))
    expected_value = fact.get("expected", MISSING)
    normalizer = str(fact.get("normalizer", "exact"))
    alternatives = fact.get("acceptableAlternatives", [])
    status = record.get("epistemicStatus") if isinstance(record, Mapping) else None
    confirmation = record.get("humanConfirmation") if isinstance(record, Mapping) else None
    confirmation_required = confirmation.get("required") if isinstance(confirmation, Mapping) else None

    if fact.get("assertion") == "no-forbidden-pattern":
        patterns = [re.compile(pattern, re.IGNORECASE) for pattern in fact.get("forbiddenPatterns", [])]
        hits = [
            {"pattern": pattern.pattern, "value": value}
            for value in strings_in(None if actual_value is MISSING else actual_value)
            for pattern in patterns
            if pattern.search(value)
        ]
        category = "missing_field" if actual_value is MISSING else (
            "false_assertion" if hits else "correct_unknown"
        )
    elif expected_unknown:
        if isinstance(record, Mapping) and status == "unknown" and actual_value is MISSING:
            category = "correct_unknown"
        elif (
            isinstance(record, Mapping)
            and status == "unknown"
            and fact.get("allowUnknownPlaceholder", False)
            and actual_value is not MISSING
            and isinstance(actual_value, str)
            and "unknown" in actual_value.casefold()
        ):
            category = "correct_unknown"
        elif actual_value is MISSING and not isinstance(record, Mapping):
            category = "missing_field"
        else:
            category = "false_assertion"
    elif actual_value is MISSING:
        category = "missing_field"
    elif expected_value is not MISSING and actual_value == expected_value:
        category = "exact_match"
    elif expected_value is not MISSING and normalize(actual_value, normalizer) == normalize(expected_value, normalizer):
        category = "normalized_match"
    elif any(normalize(actual_value, normalizer) == normalize(item, normalizer) for item in alternatives):
        if status == "inferred" and confirmation_required is True:
            category = "acceptable_inferred_difference"
        else:
            category = "false_assertion"
    else:
        category = "false_assertion"

    if fact.get("recordOptional", False) and not isinstance(record, Mapping):
        passed, failed = ["record-optional"], []
    else:
        passed, failed = validate_record_shape(record, rubric)
    if isinstance(record, Mapping):
        if record.get("field") == path:
            passed.append("field-pointer-consistency")
        else:
            failed.append("field-pointer-consistency")
        record_value = record.get("value", MISSING)
        if (actual_value is MISSING and record_value is None) or (
            actual_value is not MISSING and record_value == actual_value
        ):
            passed.append("hdp-ledger-value-consistency")
        else:
            failed.append("hdp-ledger-value-consistency")
        expected_statuses = fact.get("expectedEpistemic", [])
        if not expected_statuses or status in expected_statuses:
            passed.append("expected-epistemic-status")
        else:
            failed.append("expected-epistemic-status")
        expected_claim_classes = fact.get("expectedClaimClasses", [])
        if not expected_claim_classes or record.get("claimClass") in expected_claim_classes:
            passed.append("expected-claim-class")
        else:
            failed.append("expected-claim-class")
        sources = record.get("sources") if isinstance(record.get("sources"), list) else []
        expected_source_paths = fact.get("sourcePathsAny", [])
        if expected_unknown:
            passed.append("source-presence")
        elif sources:
            passed.append("source-presence")
        else:
            failed.append("source-presence")
        if not expected_source_paths or any(
            isinstance(source, Mapping) and source_path_matches(source, expected_source_paths)
            for source in sources
        ):
            passed.append("expected-source")
        else:
            failed.append("expected-source")
        if not fact.get("requireSourceLocation", True) or expected_unknown or any(
            isinstance(source, Mapping)
            and isinstance(source.get("location"), str)
            and bool(source["location"].strip())
            for source in sources
        ):
            passed.append("source-location")
        else:
            failed.append("source-location")
        missing_evidence = record.get("missingEvidence")
        if status in {"unknown", "inferred"}:
            if isinstance(missing_evidence, list) and len(missing_evidence) > 0:
                passed.append("missing-evidence-specificity")
            else:
                failed.append("missing-evidence-specificity")
        else:
            passed.append("missing-evidence-specificity")
        expected_confirmation = fact.get("humanConfirmation", "any")
        if (
            expected_confirmation == "any"
            or (expected_confirmation == "required" and confirmation_required is True)
            or (expected_confirmation == "not-required" and confirmation_required is False)
        ):
            passed.append("expected-human-confirmation")
        else:
            failed.append("expected-human-confirmation")

    evidence_score = len(passed) / (len(passed) + len(failed)) if passed or failed else 0.0
    if fact.get("recordOptional", False) and not isinstance(record, Mapping):
        confidence_score = 1.0
    else:
        confidence_band = fact.get("confidenceBand")
        if confidence_band is None and status in rubric["confidenceBands"]:
            confidence_band = rubric["confidenceBands"][status]
        confidence_score = bounded_score_for_band(
            record.get("confidence") if isinstance(record, Mapping) else None,
            confidence_band or [0.0, 0.0],
        )
    category_config = rubric["contentCategories"][category]
    return {
        "id": fact["id"],
        "path": path,
        "group": fact["group"],
        "critical": bool(fact.get("critical", False)),
        "weight": float(fact.get("weight", 1.0)),
        "category": category,
        "contentCredit": float(category_config["credit"]),
        "falseAssertionPenalty": float(category_config.get("penalty", 0.0)),
        "evidenceContractScore": evidence_score,
        "confidenceCalibrationScore": confidence_score,
        "evidenceChecksPassed": sorted(passed),
        "evidenceChecksFailed": sorted(failed),
        "actualValue": None if actual_value is MISSING else actual_value,
        "expectedValue": None if expected_value is MISSING else expected_value,
        "forbiddenPatternHits": hits if fact.get("assertion") == "no-forbidden-pattern" else [],
    }


def weighted_average(results: Iterable[Mapping[str, Any]], key: str) -> float:
    values = list(results)
    denominator = sum(float(item["weight"]) for item in values)
    if denominator == 0:
        return 0.0
    return sum(float(item["weight"]) * float(item[key]) for item in values) / denominator


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--actual-hdp", type=Path, required=True)
    parser.add_argument("--actual-ledger", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--expected-hdp", type=Path)
    parser.add_argument("--ignore-pointer", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    expected = load_document(args.expected)
    actual_hdp = load_document(args.actual_hdp)
    ledger = load_document(args.actual_ledger)
    rubric = load_document(args.rubric)
    records = extract_evidence_records(ledger, actual_hdp)
    records_by_path = {
        record.get("field"): record
        for record in records
        if isinstance(record, Mapping) and isinstance(record.get("field"), str)
    }

    groups = rubric["coverageGroups"]
    group_configs = {group["id"]: group for group in groups}
    manifest_errors: List[str] = []
    facts = expected.get("facts", [])
    for fact in facts:
        inferred_group = group_for_path(fact["path"], groups)
        if fact.get("group") != inferred_group:
            manifest_errors.append(
                f"{fact.get('id')}: group {fact.get('group')!r} does not match path group {inferred_group!r}"
            )
    for group in groups:
        count = sum(1 for fact in facts if fact.get("group") == group["id"])
        if count < int(group["minimumFacts"]):
            manifest_errors.append(
                f"group {group['id']} has {count} facts; requires {group['minimumFacts']}"
            )

    results = [
        classify_fact(fact, actual_hdp, records_by_path.get(fact["path"]), rubric)
        for fact in facts
    ]
    content_score = weighted_average(results, "contentCredit")
    evidence_score = weighted_average(results, "evidenceContractScore")
    confidence_score = weighted_average(results, "confidenceCalibrationScore")
    weights = rubric["scoreWeights"]
    false_penalty = sum(item["falseAssertionPenalty"] * item["weight"] for item in results)
    possible_weight = sum(item["weight"] for item in results) or 1.0
    overall_before_penalty = (
        content_score * weights["content"]
        + evidence_score * weights["evidenceContract"]
        + confidence_score * weights["confidenceCalibration"]
    )
    overall_score = max(0.0, overall_before_penalty - (false_penalty / possible_weight))
    covered_categories = {
        "exact_match",
        "normalized_match",
        "acceptable_inferred_difference",
        "correct_unknown",
        "false_assertion",
    }
    coverage = sum(item["weight"] for item in results if item["category"] in covered_categories) / possible_weight
    false_assertions = [item for item in results if item["category"] == "false_assertion"]
    critical_false_assertions = [item for item in false_assertions if item["critical"] or group_configs[item["group"]]["critical"]]

    schema_result: Dict[str, Any] = {"status": "not-run", "errors": []}
    if args.schema:
        schema_result = schema_validation(actual_hdp, load_document(args.schema))

    document_comparison: Dict[str, Any] = {"status": "not-run"}
    if args.expected_hdp:
        expected_hdp = copy.deepcopy(load_document(args.expected_hdp))
        comparable_actual = copy.deepcopy(actual_hdp)
        for pointer in args.ignore_pointer:
            remove_pointer(expected_hdp, pointer)
            remove_pointer(comparable_actual, pointer)
        expected_canonical = canonical(expected_hdp)
        actual_canonical = canonical(comparable_actual)
        exact = expected_hdp == comparable_actual
        normalized = semantic_json(expected_hdp) == semantic_json(comparable_actual)
        document_comparison = {
            "status": "pass" if exact else "fail",
            "exact": exact,
            "normalized": normalized,
            "ignoredPointers": sorted(args.ignore_pointer),
            "expectedCanonicalSha256": hashlib.sha256(expected_canonical.encode("utf-8")).hexdigest(),
            "actualCanonicalSha256": hashlib.sha256(actual_canonical.encode("utf-8")).hexdigest(),
        }

    gates = rubric["gates"]
    gate_results = {
        "goldGroupCoverage": not manifest_errors if gates["requireGoldGroupCoverage"] else True,
        "overallScore": overall_score >= gates["minimumOverallScore"],
        "contentScore": content_score >= gates["minimumContentScore"],
        "evidenceContractScore": evidence_score >= gates["minimumEvidenceContractScore"],
        "confidenceCalibrationScore": confidence_score >= gates["minimumConfidenceCalibrationScore"],
        "falseAssertions": len(false_assertions) <= gates["maximumFalseAssertions"],
        "criticalFalseAssertions": len(critical_false_assertions) <= gates["maximumCriticalFalseAssertions"],
        "coverage": coverage >= gates["minimumCoverage"],
    }
    if expected.get("expectStructuralValidity", True) and gates["requireSchemaValidationWhenExpected"]:
        gate_results["schemaValidation"] = schema_result["status"] == "pass"
    whole_document_expectation = expected.get("wholeDocumentExpectation")
    if whole_document_expectation == "exact":
        gate_results["wholeDocumentFidelity"] = document_comparison.get("exact") is True
    elif whole_document_expectation == "normalized":
        gate_results["wholeDocumentFidelity"] = document_comparison.get("normalized") is True

    report = {
        "rubricVersion": rubric["rubricVersion"],
        "fixtureId": expected.get("fixtureId"),
        "status": "pass" if all(gate_results.values()) else "fail",
        "scores": {
            "overall": round(overall_score, 6),
            "content": round(content_score, 6),
            "evidenceContract": round(evidence_score, 6),
            "confidenceCalibration": round(confidence_score, 6),
            "coverage": round(coverage, 6),
        },
        "counts": {
            category: sum(1 for item in results if item["category"] == category)
            for category in rubric["contentCategories"]
        },
        "falseAssertions": len(false_assertions),
        "criticalFalseAssertions": len(critical_false_assertions),
        "goldManifestErrors": manifest_errors,
        "schemaValidation": schema_result,
        "documentComparison": document_comparison,
        "gates": gate_results,
        "facts": results,
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
