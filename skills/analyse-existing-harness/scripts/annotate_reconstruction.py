#!/usr/bin/env python3
"""Attach complete field-level epistemic assessments to a reconstructed HDP."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Tuple

import yaml


def leaves(value: Any, path: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            if path == "/extensions" and key == "x-hdp-reconstruction":
                continue
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from leaves(value[key], f"{path}/{escaped}")
    elif isinstance(value, list):
        if not value:
            yield path, []
        for index, item in enumerate(value):
            yield from leaves(item, f"{path}/{index}")
    else:
        yield path, value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hdp", type=Path)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--overrides", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    definition = yaml.safe_load(args.hdp.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
    if not isinstance(definition, dict) or not isinstance(overrides, dict):
        parser.error("HDP and override inputs must be mappings")
    records = []
    recorded_paths = set()
    for path, value in leaves(definition):
        override = overrides.get(path, {})
        status = override.get("epistemicStatus", "unknown")
        confidence = override.get("confidence", 0.0)
        records.append(
            {
                "field": path or "/", "value": value,
                "claimClass": override.get("claimClass", "absent-or-unknowable"),
                "epistemicStatus": status, "confidence": confidence,
                "sources": override.get("sources", override.get("evidence", [])),
                "contradictions": override.get("contradictions", []),
                "missingEvidence": override.get("missingEvidence", ["No field-specific evidence supplied."]),
                "humanConfirmation": {
                    "required": override.get("humanConfirmationRequired", status in {"inferred", "unknown"}),
                    "reason": override.get("humanConfirmationReason", "Required normative value lacks sufficient source evidence." if status == "unknown" else ""),
                },
            }
        )
        recorded_paths.add(path)
    for path in sorted(
        item for item in overrides
        if isinstance(item, str) and item.startswith("/") and item not in recorded_paths
    ):
        override = overrides[path]
        if not isinstance(override, dict) or override.get("epistemicStatus") != "unknown":
            raise ValueError(
                f"absent override {path!r} must be an unknown assessment mapping"
            )
        records.append(
            {
                "field": path,
                "value": None,
                "claimClass": override.get("claimClass", "absent-or-unknowable"),
                "epistemicStatus": "unknown",
                "confidence": 0.0,
                "sources": override.get("sources", override.get("evidence", [])),
                "contradictions": override.get("contradictions", []),
                "missingEvidence": override.get(
                    "missingEvidence", ["Required source evidence is absent."]
                ),
                "humanConfirmation": {
                    "required": True,
                    "reason": override.get(
                        "humanConfirmationReason",
                        "A required normative value is absent from the source.",
                    ),
                },
            }
        )
    generation_ready = bool(overrides.get("$generationReady", False)) and not any(
        item["epistemicStatus"] == "unknown" for item in records
    )
    evidence_map = {
        "version": "0.1.0",
        "inventorySha256": hashlib.sha256(args.inventory.read_bytes()).hexdigest(),
        "inventory": inventory.get("files", []),
        "contradictions": overrides.get("$contradictions", []),
        "omissions": overrides.get("$omissions", []),
        "records": records,
    }
    try:
        evidence_ref = args.report.resolve().relative_to(args.output.resolve().parent).as_posix()
    except ValueError:
        evidence_ref = str(args.report.resolve())
    definition.setdefault("extensions", {})["x-hdp-reconstruction"] = {
        "evidenceMap": evidence_ref,
        "generationReady": generation_ready,
        "sourceMode": "skill-assisted-reconstruction",
    }
    args.output.write_text(yaml.safe_dump(definition, sort_keys=False), encoding="utf-8")
    args.report.write_text(json.dumps(evidence_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"fieldAssessmentCount": len(records), "generationReady": generation_ready}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
