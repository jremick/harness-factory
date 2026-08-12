import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import yaml

from hdp.analyser import analyse_harness
from hdp.compiler import compile_hdp


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "skills" / "analyse-existing-harness" / "scripts" / "validate_reconstruction.py"
SCHEMA = ROOT / "skills" / "analyse-existing-harness" / "references" / "hdp.schema.json"
CANONICAL_SCHEMA = ROOT / "src" / "hdp" / "schemas" / "hdp.schema.json"
EXAMPLE = ROOT / "examples" / "software-development" / "hdp.yaml"


def _leaves(value, path=""):
    if isinstance(value, dict):
        for key in sorted(value):
            if path == "/extensions" and key == "x-hdp-reconstruction":
                continue
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from _leaves(value[key], f"{path}/{escaped}")
    elif isinstance(value, list):
        if not value:
            yield path, value
        for index, item in enumerate(value):
            yield from _leaves(item, f"{path}/{index}")
    else:
        yield path, value


def _reconstruction():
    definition = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    assessments = [
        {
            "path": path,
            "value": value,
            "claimClass": "absent-or-unknowable",
            "epistemicStatus": "unknown",
            "confidence": 0,
            "evidence": [],
            "contradictions": [],
            "missingEvidence": ["Test fixture has no reconstruction evidence."],
            "humanConfirmationRequired": True,
        }
        for path, value in _leaves(definition)
    ]
    definition.setdefault("extensions", {})["x-hdp-reconstruction"] = {
        "schemaVersion": "1",
        "generationReady": False,
        "inventorySha256": "0" * 64,
        "inventory": [],
        "contradictions": [],
        "omissions": [],
        "fieldAssessments": assessments,
    }
    return definition


def _run(tmp_path, definition):
    hdp = tmp_path / "hdp.reconstructed.yaml"
    hdp.write_text(yaml.safe_dump(definition, sort_keys=False), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(hdp), "--schema", str(SCHEMA)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )


def test_skill_schema_matches_canonical_schema_byte_for_byte():
    assert SCHEMA.read_bytes() == CANONICAL_SCHEMA.read_bytes()


def test_reconstruction_schema_accepts_compact_and_inline_variants():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    compact = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    compact.setdefault("extensions", {})["x-hdp-reconstruction"] = {
        "evidenceMap": "evidence-map.json",
        "generationReady": False,
        "sourceMode": "declared-source-recovery",
    }

    assert list(validator.iter_errors(compact)) == []
    assert list(validator.iter_errors(_reconstruction())) == []

    envelope = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    envelope.setdefault("extensions", {})["x-hdp-reconstruction"] = {
        "owner": "https://example.invalid/hdp-reconstruction",
        "schemaUri": "https://example.invalid/hdp-reconstruction.schema.json",
        "schemaDigest": "sha256:" + "0" * 64,
        "version": "1.0.0",
        "required": False,
        "payload": {},
    }
    assert list(validator.iter_errors(envelope)) == []


def test_cli_rejects_forged_assessment_value(tmp_path):
    definition = _reconstruction()
    assessments = definition["extensions"]["x-hdp-reconstruction"]["fieldAssessments"]
    assessment = next(item for item in assessments if item["path"] == "/metadata/name")
    assessment["value"] = "forged-name"

    result = _run(tmp_path, definition)

    assert result.returncode == 2
    assert "assessment /metadata/name: value does not match HDP value" in result.stdout


def test_cli_rejects_unresolved_measure_reference(tmp_path):
    definition = _reconstruction()
    definition["evaluation"]["metrics"][0]["measureId"] = "MEASURE-DOES-NOT-EXIST"
    assessments = definition["extensions"]["x-hdp-reconstruction"]["fieldAssessments"]
    assessment = next(
        item for item in assessments if item["path"] == "/evaluation/metrics/0/measureId"
    )
    assessment["value"] = "MEASURE-DOES-NOT-EXIST"

    result = _run(tmp_path, definition)

    assert result.returncode == 2
    assert "measureId references unknown id 'MEASURE-DOES-NOT-EXIST'" in result.stdout


def test_cli_rejects_duplicate_yaml_keys(tmp_path):
    hdp = tmp_path / "duplicate.yaml"
    hdp.write_text("kind: HarnessDefinition\nkind: HarnessDefinition\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(hdp), "--schema", str(SCHEMA)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "found duplicate key 'kind'" in result.stdout


def _analysed_public_projection(tmp_path):
    harness = tmp_path / "harness"
    analysis = tmp_path / "analysis"
    binding = ROOT / "examples/software-development/bindings/codex.yaml"
    assert compile_hdp(EXAMPLE, binding, harness).status == "pass"
    analyse_harness(harness, analysis)
    return harness, analysis


def test_analyser_public_projection_validates_with_adjacent_evidence_map(tmp_path):
    harness, analysis = _analysed_public_projection(tmp_path)
    hdp = analysis / "hdp.reconstructed.yaml"

    result = subprocess.run(
        [
            sys.executable, str(SCRIPT), str(hdp), "--schema", str(SCHEMA),
            "--inventory", str(analysis / "source-inventory.json"),
            "--root", str(harness),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID" in result.stdout


def test_exact_reconstruction_unknowns_fail_when_marked_generation_ready(tmp_path):
    _, analysis = _analysed_public_projection(tmp_path)
    hdp = analysis / "hdp.reconstructed.yaml"
    evidence_path = analysis / "evidence-map.json"
    evidence_map = json.loads(evidence_path.read_text(encoding="utf-8"))
    record = next(
        item for item in evidence_map["records"]
        if item["field"] == "/evaluation/tests/0/expected"
    )
    record["epistemicStatus"] = "unknown"
    record["confidence"] = 0
    record["sources"] = []
    record["missingEvidence"] = ["Authoritative evaluator contract is unavailable."]
    record["humanConfirmation"] = {"required": True, "reason": "Missing evidence."}
    evidence_path.write_text(json.dumps(evidence_map), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(hdp), "--schema", str(SCHEMA)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "generationReady cannot be true while unknown fields remain" in result.stdout


def test_public_projection_rejects_fabricated_absent_field_value(tmp_path):
    _, analysis = _analysed_public_projection(tmp_path)
    evidence_path = analysis / "evidence-map.json"
    evidence_map = json.loads(evidence_path.read_text(encoding="utf-8"))
    record = next(
        item for item in evidence_map["records"]
        if item["field"] == "/evaluation/tests/0/expected"
    )
    record["value"] = "fabricated hidden expected value"
    evidence_path.write_text(json.dumps(evidence_map), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            str(analysis / "hdp.reconstructed.yaml"), "--schema", str(SCHEMA),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "assessment /evaluation/tests/0/expected" in result.stdout
