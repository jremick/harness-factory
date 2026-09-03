from __future__ import annotations

import base64
import io
import json
import hashlib
import os
import tarfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from hdp import __version__
from hdp.bindings import load_codex_binding
from hdp.cli import app, harness_app, harness_main, main
from hdp.cli_contract import (
    CLI_CONTRACT_VERSION,
    COMPATIBILITY_ALIASES,
    COMPATIBILITY_COMMANDS,
    COMMAND_OPTION_FLAGS,
    COMMAND_FLAG_PARAMETERS,
    COMMAND_PARAMETER_NAMES,
    COMMAND_REQUIRED_PARAMETERS,
    PRODUCT_COMMANDS,
    SUPPORTED_GENERATED_MANIFEST_VERSION,
    SUPPORTED_INSTALL_MANIFEST_VERSION,
    SUPPORTED_RELEASE_MANIFEST_VERSION,
    unsupported_version_message,
)
from hdp.compiler import _compilable_document, compile_hdp
from hdp.conformance import stable_binding_identity
from hdp.diagnostics import HdpInputError
from hdp.io import load_document
from hdp.normalise import normalise_hdp
from hdp.packaging import _entries, _sha256_bytes, package_release, verify_release
from hdp.project import install_harness
from typer.main import get_command


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "software-development" / "hdp.yaml"
BINDING = ROOT / "examples" / "software-development" / "bindings" / "codex.yaml"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "compatibility"
RUNNER = CliRunner()


def _json_stdout(result) -> dict:
    assert result.stdout.strip(), result.stderr
    value = json.loads(result.stdout)
    assert isinstance(value, dict)
    return value


def _assert_cli_markers(value: dict, command: str) -> None:
    assert value["cliContractVersion"] == CLI_CONTRACT_VERSION
    assert value["command"] == command
    assert value["factoryVersion"] == __version__


def _copy_as_json(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    destination.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _unpack_alpha_generated_fixture(destination: Path) -> Path:
    descriptor = json.loads((FIXTURE_ROOT / "alpha-generated.json").read_text())
    encoded = b"".join((FIXTURE_ROOT / descriptor["bundle"]).read_bytes().split())
    compressed = base64.b64decode(encoded, validate=True)
    assert hashlib.sha256(compressed).hexdigest() == descriptor["bundleSha256"]
    with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
        for member in archive.getmembers():
            name = Path(member.name)
            if (
                not member.name.startswith("generated/")
                or member.name.startswith("generated/._")
                or "/._" in member.name
                or member.name == "generated/"
                or name.is_absolute()
                or ".." in name.parts
            ):
                continue
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            assert member.isfile(), member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            assert source is not None
            target.write_bytes(source.read())
            os.chmod(target, member.mode & 0o7777)
    harness = destination / "generated"
    manifest_bytes = (harness / ".hdp/manifest.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == descriptor["rootManifestSha256"]
    assert hashlib.sha256((harness / ".hdp/runtime-policy.json").read_bytes()).hexdigest() == descriptor[
        "runtimePolicySha256"
    ]
    assert hashlib.sha256((harness / "scripts/harnessctl.py").read_bytes()).hexdigest() == descriptor[
        "harnessctlSha256"
    ]
    manifest = json.loads(manifest_bytes)
    assert len(manifest["artifacts"]) == descriptor["artifactCount"]
    for artifact in manifest["artifacts"]:
        content = (harness / artifact["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
    return harness


def test_real_entry_points_make_no_argument_help_successful(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness_main([]) == 0
    harness_output = capsys.readouterr()
    assert "Usage: harness" in harness_output.out
    assert harness_output.err == ""

    assert main([]) == 0
    hdp_output = capsys.readouterr()
    assert "Usage: hdp" in hdp_output.out
    assert hdp_output.err == ""


def test_beta_command_surface_is_frozen() -> None:
    assert tuple(command.name for command in harness_app.registered_commands) == PRODUCT_COMMANDS

    registered = tuple(command.name for command in app.registered_commands)
    assert len(registered) == len(COMPATIBILITY_COMMANDS) + len(COMPATIBILITY_ALIASES)
    assert tuple(name for name in registered if name not in COMPATIBILITY_ALIASES) == COMPATIBILITY_COMMANDS
    assert tuple(name for name in registered if name in COMPATIBILITY_ALIASES) == COMPATIBILITY_ALIASES
    assert set(COMMAND_OPTION_FLAGS) == set(registered)
    for cli, names in (
        (harness_app, PRODUCT_COMMANDS),
        (app, COMPATIBILITY_COMMANDS + COMPATIBILITY_ALIASES),
    ):
        command_group = get_command(cli)
        assert len(command_group.commands) == len(names)
        assert set(command_group.commands) == set(names)
        for name in names:
            command = command_group.commands[name]
            assert tuple(parameter.name for parameter in command.params) == COMMAND_PARAMETER_NAMES[name]
            assert all(parameter.nargs == 1 for parameter in command.params)
            assert tuple(
                parameter.name for parameter in command.params if parameter.required
            ) == COMMAND_REQUIRED_PARAMETERS[name]
            assert tuple(
                parameter.name
                for parameter in command.params
                if getattr(parameter, "is_flag", False)
            ) == COMMAND_FLAG_PARAMETERS[name]
            actual = tuple(
                flag
                for parameter in command.params
                for flag in parameter.opts
                if flag.startswith("--")
            )
            assert actual == COMMAND_OPTION_FLAGS[name], name
    assert all(
        command.hidden
        for command in app.registered_commands
        if command.name in COMPATIBILITY_ALIASES
    )


def test_version_diagnostics_identify_marker_types() -> None:
    numeric = unsupported_version_message("HDP definition", 1, "0.1.0")
    string = unsupported_version_message("HDP definition", "1", "0.1.0")
    assert "1 (number)" in numeric
    assert "'1' (string)" in string
    assert numeric != string


def test_init_accepts_json_and_preserves_json_default(tmp_path: Path) -> None:
    explicit = RUNNER.invoke(
        harness_app,
        ["init", str(tmp_path / "explicit"), "--template", "empty", "--json"],
    )
    assert explicit.exit_code == 0, explicit.stderr
    explicit_value = _json_stdout(explicit)
    _assert_cli_markers(explicit_value, "init")
    assert explicit_value["status"] == "initialized-incomplete"
    assert "INITIALIZED" not in explicit.stdout

    established = RUNNER.invoke(
        harness_app,
        ["init", str(tmp_path / "established"), "--template", "empty"],
    )
    assert established.exit_code == 0, established.stderr
    established_value = _json_stdout(established)
    _assert_cli_markers(established_value, "init")
    assert established_value["status"] == "initialized-incomplete"


def test_audit_defaults_to_human_stdout(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    compile_hdp(EXAMPLE, BINDING, harness)

    result = RUNNER.invoke(
        harness_app,
        ["audit", str(harness), "--output", str(tmp_path / "analysis")],
    )

    assert result.exit_code == 0, result.stderr
    assert result.stdout.startswith("AUDITED ")
    assert "{\n" not in result.stdout
    assert result.stderr == ""


def test_audit_json_includes_ahds_status_marker(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    compile_hdp(EXAMPLE, BINDING, harness)

    result = RUNNER.invoke(
        harness_app,
        ["audit", str(harness), "--output", str(tmp_path / "analysis"), "--json"],
    )

    assert result.exit_code == 0, result.stderr
    value = _json_stdout(result)
    _assert_cli_markers(value, "audit")
    assert value["status"] == "pass"


def test_product_json_outputs_are_single_marked_objects(tmp_path: Path) -> None:
    project = tmp_path / "project"
    target = tmp_path / "target"
    target.mkdir()

    init = RUNNER.invoke(harness_app, ["init", str(project), "--template", "codex-sdlc", "--json"])
    assert init.exit_code == 0, init.stderr
    _assert_cli_markers(_json_stdout(init), "init")

    build = RUNNER.invoke(harness_app, ["build", str(project), "--json"])
    assert build.exit_code == 0, build.stderr
    _assert_cli_markers(_json_stdout(build), "build")

    preview = RUNNER.invoke(
        harness_app,
        ["install", str(target), "--project", str(project), "--dry-run", "--json"],
    )
    assert preview.exit_code == 0, preview.stderr
    _assert_cli_markers(_json_stdout(preview), "install")

    verify = RUNNER.invoke(harness_app, ["verify", str(project), "--json"])
    assert verify.exit_code == 0, verify.stderr
    _assert_cli_markers(_json_stdout(verify), "verify")

    doctor = RUNNER.invoke(harness_app, ["doctor", "--json"])
    assert doctor.exit_code == 0, doctor.stderr
    doctor_value = _json_stdout(doctor)
    _assert_cli_markers(doctor_value, "doctor")
    assert doctor_value["version"] == doctor_value["factoryVersion"]


def test_install_with_explicit_harness_does_not_discover_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = tmp_path / "generated"
    target = tmp_path / "target"
    live_target = tmp_path / "live-target"
    target.mkdir()
    live_target.mkdir()
    compile_hdp(EXAMPLE, BINDING, harness)

    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    result = RUNNER.invoke(
        harness_app,
        [
            "install",
            str(target),
            "--harness",
            str(harness),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stderr
    value = _json_stdout(result)
    _assert_cli_markers(value, "install")
    assert value["status"] == "planned"

    live = RUNNER.invoke(
        harness_app,
        [
            "install",
            str(live_target),
            "--harness",
            str(harness),
            "--json",
        ],
    )
    assert live.exit_code == 0, live.stderr
    assert _json_stdout(live)["status"] == "installed"


def test_strict_partial_result_keeps_machine_stdout_and_human_diagnostic_on_stderr(
    tmp_path: Path,
) -> None:
    harness = tmp_path / "foreign"
    harness.mkdir()
    (harness / "AGENTS.md").write_text("Run the tests.\n", encoding="utf-8")

    result = RUNNER.invoke(
        harness_app,
        ["audit", str(harness), "--output", str(tmp_path / "analysis"), "--json"],
    )

    assert result.exit_code == 2
    value = _json_stdout(result)
    _assert_cli_markers(value, "audit")
    assert value["valid"] is False
    assert value["status"] == "fail"
    assert "ERROR:" in result.stderr
    assert "ERROR:" not in result.stdout


def test_allow_partial_audit_json_is_marked_failed_without_stderr(
    tmp_path: Path,
) -> None:
    harness = tmp_path / "foreign"
    harness.mkdir()
    (harness / "AGENTS.md").write_text("Run the tests.\n", encoding="utf-8")

    result = RUNNER.invoke(
        harness_app,
        [
            "audit",
            str(harness),
            "--output",
            str(tmp_path / "analysis"),
            "--allow-partial",
            "--json",
        ],
    )

    assert result.exit_code == 0
    value = _json_stdout(result)
    _assert_cli_markers(value, "audit")
    assert value["status"] == "fail"
    assert value["valid"] is False
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("relative", "field"),
    [
        (".hdp/manifest.json", "manifestVersion"),
        (".hdp/hir.json", "hir_version"),
        (".hdp/hir.json", "source_hdp_version"),
        (".hdp/hir.json", "canonical_semantics.hdpVersion"),
        (".hdp/source-definition.public.json", "hdpVersion"),
        (".hdp/runtime-policy.json", "bindingVersion"),
        (".hdp/runtime-policy.json", "adapterVersion"),
    ],
)
def test_audit_rejects_incompatible_generated_subject_versions(
    tmp_path: Path, relative: str, field: str
) -> None:
    harness = tmp_path / "harness"
    compile_hdp(EXAMPLE, BINDING, harness)
    path = harness / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    if field == "canonical_semantics.hdpVersion":
        value["canonical_semantics"]["hdpVersion"] = "0.2.0"
    else:
        value[field] = "0.2.0"
    path.write_text(json.dumps(value), encoding="utf-8")

    result = RUNNER.invoke(
        harness_app,
        ["audit", str(harness), "--output", str(tmp_path / "analysis"), "--json"],
    )

    assert result.exit_code == 2
    value = _json_stdout(result)
    assert value["valid"] is False
    assert value["subjectStatus"] == "fail"
    assert value["subjectDiagnostics"]


def test_audit_rejects_missing_embedded_subject_metadata(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    compile_hdp(EXAMPLE, BINDING, harness)
    (harness / ".hdp/hir.json").unlink()

    result = RUNNER.invoke(
        harness_app,
        ["audit", str(harness), "--output", str(tmp_path / "analysis"), "--json"],
    )

    assert result.exit_code == 2
    value = _json_stdout(result)
    assert value["valid"] is False
    assert "hir.json" in value["subjectDiagnostics"][0]


def test_exit_classes_include_non_parity_and_operational_input_failure(
    tmp_path: Path,
) -> None:
    left = tmp_path / "left.yaml"
    right = tmp_path / "right.yaml"
    left.write_bytes(EXAMPLE.read_bytes())
    changed = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    changed["metadata"]["title"] = "Changed title"
    right.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")

    non_parity = RUNNER.invoke(app, ["diff", str(left), str(right)])
    assert non_parity.exit_code == 1
    value = _json_stdout(non_parity)
    _assert_cli_markers(value, "diff")
    assert value["parity"] is False
    assert "ERROR:" not in non_parity.stdout

    operational = RUNNER.invoke(
        harness_app, ["build", str(tmp_path / "missing-project"), "--json"]
    )
    assert operational.exit_code == 3
    assert operational.stdout == ""
    assert "ERROR:" in operational.stderr


def test_alpha_root_json_fixture_builds_and_verifies(tmp_path: Path) -> None:
    fixture = json.loads(
        (FIXTURE_ROOT / "alpha-root-json.json").read_text(encoding="utf-8")
    )
    project = tmp_path / "alpha-project"
    source_definition = ROOT / fixture["sourceDefinition"]
    source_binding = ROOT / fixture["sourceBinding"]
    assert hashlib.sha256(source_definition.read_bytes()).hexdigest() == fixture[
        "sourceDefinitionSha256"
    ]
    assert hashlib.sha256(source_binding.read_bytes()).hexdigest() == fixture[
        "sourceBindingSha256"
    ]
    _copy_as_json(source_definition, project / fixture["definitionPath"])
    _copy_as_json(source_binding, project / fixture["bindingPath"])
    target = tmp_path / "target"
    target.mkdir()

    build = RUNNER.invoke(harness_app, ["build", str(project), "--json"])
    assert build.exit_code == 0, build.stderr
    build_value = _json_stdout(build)
    _assert_cli_markers(build_value, "build")
    assert build_value["manifest"]["manifestVersion"] == SUPPORTED_GENERATED_MANIFEST_VERSION

    preview = RUNNER.invoke(
        harness_app,
        ["install", str(target), "--project", str(project), "--dry-run", "--json"],
    )
    assert preview.exit_code == 0, preview.stderr
    _assert_cli_markers(_json_stdout(preview), "install")

    installed = RUNNER.invoke(
        harness_app, ["install", str(target), "--project", str(project), "--json"]
    )
    assert installed.exit_code == 0, installed.stderr
    _assert_cli_markers(_json_stdout(installed), "install")

    install_manifest = load_document(target / ".harness-factory/install-manifest.json")
    assert install_manifest["manifestVersion"] == SUPPORTED_INSTALL_MANIFEST_VERSION

    verify = RUNNER.invoke(harness_app, ["verify", str(project), "--json"])
    assert verify.exit_code == 0, verify.stderr
    _assert_cli_markers(_json_stdout(verify), "verify")


def test_init_build_live_install_then_strict_audit_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    target = tmp_path / "target"
    target.mkdir()

    assert RUNNER.invoke(
        harness_app,
        ["init", str(project), "--template", "codex-sdlc", "--json"],
    ).exit_code == 0
    assert RUNNER.invoke(harness_app, ["build", str(project), "--json"]).exit_code == 0
    installed = RUNNER.invoke(
        harness_app,
        ["install", str(target), "--project", str(project), "--json"],
    )
    assert installed.exit_code == 0, installed.stderr
    (target / "README.md").write_text("pre-existing repository content\n", encoding="utf-8")

    audited = RUNNER.invoke(
        harness_app,
        ["audit", str(target), "--output", str(tmp_path / "analysis"), "--json"],
    )
    assert audited.exit_code == 0, audited.stderr
    value = _json_stdout(audited)
    _assert_cli_markers(value, "audit")
    assert value["valid"] is True

    ownership_path = target / ".harness-factory/install-manifest.json"
    ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
    ownership["files"][0]["sha256"] = "0" * 64
    ownership_path.write_text(json.dumps(ownership, sort_keys=True) + "\n", encoding="utf-8")
    rejected = RUNNER.invoke(
        harness_app,
        ["audit", str(target), "--output", str(tmp_path / "analysis-rejected"), "--json"],
    )
    assert rejected.exit_code == 2
    assert _json_stdout(rejected)["valid"] is False
    assert any("ownership" in item for item in _json_stdout(rejected)["subjectDiagnostics"])

    first_owned = ownership["files"][0]["path"]
    ownership["files"][0]["sha256"] = hashlib.sha256(
        (target / first_owned).read_bytes()
    ).hexdigest()
    ownership_path.write_text(json.dumps(ownership, sort_keys=True) + "\n", encoding="utf-8")
    (target / ".harness-factory/rogue.json").write_text("{}\n", encoding="utf-8")
    rogue = RUNNER.invoke(
        harness_app,
        ["audit", str(target), "--output", str(tmp_path / "analysis-rogue"), "--json"],
    )
    assert rogue.exit_code == 2
    assert any("installer control" in item for item in _json_stdout(rogue)["subjectDiagnostics"])


def test_immutable_alpha_generated_fixture_installs_audits_packages_and_verifies(
    tmp_path: Path,
) -> None:
    harness = _unpack_alpha_generated_fixture(tmp_path / "alpha")
    target = tmp_path / "target"
    target.mkdir()

    installed = RUNNER.invoke(
        harness_app,
        ["install", str(target), "--harness", str(harness), "--json"],
    )
    assert installed.exit_code == 0, installed.stderr
    audited = RUNNER.invoke(
        harness_app,
        ["audit", str(target), "--output", str(tmp_path / "analysis"), "--json"],
    )
    assert audited.exit_code == 0, audited.stderr
    assert _json_stdout(audited)["valid"] is True

    release = tmp_path / "release"
    package_release(harness, EXAMPLE, BINDING, release)
    verified = verify_release(release)
    assert verified["verified"] is True, verified


@pytest.mark.parametrize("invalid_kind", ["schema", "semantic"])
def test_release_rebound_invalid_semantics_fail_before_digest_only(
    tmp_path: Path, invalid_kind: str
) -> None:
    harness = tmp_path / "harness"
    release = tmp_path / "release"
    compile_hdp(EXAMPLE, BINDING, harness)
    package_release(harness, EXAMPLE, BINDING, release)

    resolved_hir_path = release / "payload/resolved-hir.json"
    raw_hir = json.loads(resolved_hir_path.read_text(encoding="utf-8"))
    semantics = raw_hir["canonical_semantics"]
    if invalid_kind == "schema":
        # This remains normalisable but violates the canonical JSON Schema.
        semantics["metadata"]["title"] = 17
    else:
        # This remains structurally valid but violates a generation invariant.
        semantics["requirements"][0]["status"] = "proposed"
    rebound = normalise_hdp(
        _compilable_document(semantics),
        binding_ref=stable_binding_identity(load_codex_binding(BINDING)),
    )
    resolved_hir_path.write_text(
        json.dumps(rebound.canonical_dict(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    # Rebind the release file set and payload digest so the targeted failure
    # cannot be explained by a stale outer release digest.
    payload = release / "payload"
    records = _entries(payload)
    manifest_path = release / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = records
    manifest["payloadDigest"] = _sha256_bytes(
        json.dumps(records, separators=(",", ":"), sort_keys=True).encode()
    )
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    result = verify_release(release)
    assert result["verified"] is False
    expected = "schema validation" if invalid_kind == "schema" else "semantic validation"
    assert any(expected in error for error in result["errors"]), result["errors"]
    assert not any("payload set digest mismatch" in error for error in result["errors"])


def test_legacy_hdp_compile_and_generate_aliases_emit_their_operation_marker(
    tmp_path: Path,
) -> None:
    compile_result = RUNNER.invoke(
        app,
        [
            "compile",
            str(EXAMPLE),
            "--binding",
            str(BINDING),
            "--output",
            str(tmp_path / "compile"),
        ],
    )
    assert compile_result.exit_code == 0, compile_result.stderr
    _assert_cli_markers(_json_stdout(compile_result), "compile")

    generate_result = RUNNER.invoke(
        app,
        [
            "generate",
            str(EXAMPLE),
            "--binding",
            str(BINDING),
            "--output",
            str(tmp_path / "generate"),
        ],
    )
    assert generate_result.exit_code == 0, generate_result.stderr
    _assert_cli_markers(_json_stdout(generate_result), "generate")


def test_unsupported_hdp_version_fails_before_generation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "hdp.json").write_text(
        (FIXTURE_ROOT / "unsupported-hdp-version.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _copy_as_json(BINDING, project / "bindings/codex.json")

    result = RUNNER.invoke(harness_app, ["build", str(project), "--json"])

    assert result.exit_code == 3
    assert result.stdout == ""
    assert unsupported_version_message("HDP definition", "0.2.0", "0.1.0") in result.stderr
    assert not (project / "build").exists()


def test_validate_unsupported_hdp_version_has_marked_json_diagnostic(tmp_path: Path) -> None:
    definition = tmp_path / "unsupported.json"
    definition.write_text(
        (FIXTURE_ROOT / "unsupported-hdp-version.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = RUNNER.invoke(app, ["validate", str(definition), "--json"])

    assert result.exit_code == 2
    value = _json_stdout(result)
    _assert_cli_markers(value, "validate")
    assert any(
        diagnostic["code"] == "HDP-COMPAT-UNSUPPORTED-VERSION"
        and "No automatic migration is provided" in diagnostic["message"]
        for diagnostic in value["diagnostics"]
    )


def test_unsupported_binding_version_fails_before_generation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _copy_as_json(EXAMPLE, project / "hdp.json")
    binding = json.loads(
        (FIXTURE_ROOT / "unsupported-binding-version.json").read_text(encoding="utf-8")
    )
    (project / "bindings").mkdir()
    (project / "bindings/codex.json").write_text(
        json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    result = RUNNER.invoke(harness_app, ["build", str(project), "--json"])

    assert result.exit_code == 3
    assert result.stdout == ""
    assert unsupported_version_message("Codex target binding", "0.2.0", "0.1.0") in result.stderr
    assert not (project / "build").exists()


def test_unsupported_generated_manifest_is_rejected_without_install_write(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    target = tmp_path / "target"
    target.mkdir()
    compile_hdp(EXAMPLE, BINDING, harness)
    manifest_path = harness / ".hdp/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifestVersion"] = "0.1.0"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    with pytest.raises(HdpInputError, match="unsupported generated harness manifest version"):
        install_harness(harness, target, dry_run=False)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize(
    "manifest_text",
    [
        "{}",
        '{"manifestVersion":"1","manifestVersion":"1","sourceDefinition":{},"sourceGenerator":{},"files":[]}',
    ],
)
def test_invalid_ownership_manifest_blocks_dry_run_and_live_before_managed_writes(
    tmp_path: Path, manifest_text: str
) -> None:
    harness = tmp_path / "harness"
    target = tmp_path / "target"
    compile_hdp(EXAMPLE, BINDING, harness)
    target.mkdir()
    (target / ".harness-factory").mkdir()
    ownership = target / ".harness-factory/install-manifest.json"
    ownership.write_text(manifest_text, encoding="utf-8")

    for dry_run in (True, False):
        result = RUNNER.invoke(
            harness_app,
            [
                "install",
                str(target),
                "--harness",
                str(harness),
                *( ["--dry-run"] if dry_run else [] ),
                "--json",
            ],
        )
        assert result.exit_code == 3
        assert result.stdout == ""
        assert "installation manifest" in result.stderr or "duplicate key" in result.stderr
    assert not (target / "AGENTS.md").exists()
    assert not (target / ".harness-factory/install.lock").exists()


def test_duplicate_generated_manifest_blocks_install_before_writes(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    target = tmp_path / "target"
    compile_hdp(EXAMPLE, BINDING, harness)
    target.mkdir()
    manifest = harness / ".hdp/manifest.json"
    manifest.write_text(
        '{"manifestVersion":"1","manifestVersion":"1","artifacts":[]}',
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        harness_app,
        ["install", str(target), "--harness", str(harness), "--json"],
    )

    assert result.exit_code == 3
    assert result.stdout == ""
    assert "duplicate key" in result.stderr
    assert not (target / "AGENTS.md").exists()


def test_opaque_journal_conflict_is_same_dry_run_and_live_json_exit(
    tmp_path: Path,
) -> None:
    harness = tmp_path / "harness"
    target = tmp_path / "target"
    compile_hdp(EXAMPLE, BINDING, harness)
    target.mkdir()
    journal = target / ".harness-factory/install-transaction.json"
    journal.parent.mkdir()
    opaque = b"not-json-and-never-read\n"
    journal.write_bytes(opaque)

    results = []
    for dry_run in (True, False):
        result = RUNNER.invoke(
            harness_app,
            [
                "install",
                str(target),
                "--harness",
                str(harness),
                *( ["--dry-run"] if dry_run else [] ),
                "--json",
            ],
        )
        assert result.exit_code == 2
        value = _json_stdout(result)
        _assert_cli_markers(value, "install")
        assert value["status"] == "conflict"
        assert "manual recovery" in value["conflicts"][0]["reason"]
        assert "manual recovery" in result.stderr
        assert "not-json" not in result.stderr
        assert journal.read_bytes() == opaque
        results.append(value)
    assert [value["status"] for value in results] == ["conflict", "conflict"]
    assert results[0]["conflicts"] == results[1]["conflicts"]
    assert not (target / "AGENTS.md").exists()


def test_unsupported_release_manifest_reports_closed_failure(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    release = tmp_path / "release"
    compile_hdp(EXAMPLE, BINDING, harness)
    package_release(harness, EXAMPLE, BINDING, release)
    manifest_path = release / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifestVersion"] = "0.2.0"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = verify_release(release)

    assert result["verified"] is False
    assert any(
        unsupported_version_message("release manifest", "0.2.0", SUPPORTED_RELEASE_MANIFEST_VERSION)
        in error
        for error in result["errors"]
    )


@pytest.mark.parametrize(
    "marker",
    ["hir_version", "source_hdp_version", "canonical_semantics.hdpVersion"],
)
def test_release_verification_requires_explicit_raw_hir_version_markers(
    tmp_path: Path, marker: str
) -> None:
    harness = tmp_path / "harness"
    release = tmp_path / "release"
    compile_hdp(EXAMPLE, BINDING, harness)
    package_release(harness, EXAMPLE, BINDING, release)
    path = release / "payload/resolved-hir.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if marker == "canonical_semantics.hdpVersion":
        value["canonical_semantics"].pop("hdpVersion")
    else:
        value.pop(marker)
    path.write_text(json.dumps(value), encoding="utf-8")

    result = verify_release(release)

    assert result["verified"] is False
    assert any("resolved HIR" in error for error in result["errors"])


@pytest.mark.parametrize("content", ["not-json", "[]"])
def test_verify_release_input_errors_emit_no_json_and_exit_three(
    tmp_path: Path, content: str
) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "release-manifest.json").write_text(content, encoding="utf-8")

    result = RUNNER.invoke(app, ["verify-release", str(release)])

    assert result.exit_code == 3
    assert result.stdout == ""
    assert "release manifest" in result.stderr


def test_verify_release_parsed_failure_keeps_json_and_exit_two(tmp_path: Path) -> None:
    harness = tmp_path / "harness"
    release = tmp_path / "release"
    compile_hdp(EXAMPLE, BINDING, harness)
    package_release(harness, EXAMPLE, BINDING, release)
    (release / "payload/harness/AGENTS.md").write_text("tampered\n", encoding="utf-8")

    result = RUNNER.invoke(app, ["verify-release", str(release)])

    assert result.exit_code == 2
    value = _json_stdout(result)
    _assert_cli_markers(value, "verify-release")
    assert value["verified"] is False
