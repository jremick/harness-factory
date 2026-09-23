"""An installed harness shares a repository with unrelated dependency trees."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hdp.cli import harness_app
from hdp.diagnostics import HdpGenerationError
from hdp.packaging import package_release


RUNNER = CliRunner()


@pytest.fixture
def installed(tmp_path: Path):
    project, target = tmp_path / "project", tmp_path / "target"
    target.mkdir()
    for args in (
        ["init", str(project), "--template", "codex-sdlc", "--json"],
        ["build", str(project), "--json"],
        ["install", str(target), "--project", str(project), "--json"],
    ):
        result = RUNNER.invoke(harness_app, args)
        assert result.exit_code == 0, result.stderr
    return project, target


def audit(target: Path, output: Path):
    return RUNNER.invoke(harness_app, ["audit", str(target), "--output", str(output), "--json"])


def dependency_link(target: Path, directory="node_modules", destination="../fixture.py"):
    dependency = target / directory
    binary = dependency / (".bin" if directory == "node_modules" else "bin")
    binary.mkdir(parents=True)
    (dependency / "fixture.py").write_text("# Synthetic dependency; never executed.\n")
    (binary / "fixture").symlink_to(destination)


@pytest.mark.parametrize("directory", ["node_modules", ".venv"])
@pytest.mark.parametrize("destination", ["../fixture.py", "../missing", "outside"])
def test_dependency_links_do_not_change_installed_subject(installed, tmp_path, directory, destination):
    _, target = installed
    baseline_output = tmp_path / "baseline"
    baseline = audit(target, baseline_output)
    assert baseline.exit_code == 0, baseline.stderr
    before = json.loads((baseline_output / "coverage-report.json").read_text())["subject"]
    ownership = json.loads((target / ".harness-factory/install-manifest.json").read_text())
    hashes = {item["path"]: hashlib.sha256((target / item["path"]).read_bytes()).hexdigest()
              for item in ownership["files"]}
    if destination == "outside":
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "unrelated.txt").write_text("Synthetic unrelated content.\n")
        destination = str(outside)
    dependency_link(target, directory, destination)

    output = tmp_path / "with-dependencies"
    result = audit(target, output)
    assert result.exit_code == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["status"] == "pass" and value["valid"] is True
    assert json.loads((output / "coverage-report.json").read_text())["subject"] == before
    inventory = json.loads((output / "source-inventory.json").read_text())
    assert all(not item["path"].startswith(directory + "/") for item in inventory["files"])
    assert hashes == {name: hashlib.sha256((target / name).read_bytes()).hexdigest() for name in hashes}


@pytest.mark.parametrize("relative", [
    "AGENTS.md", ".hdp/source-definition.public.json", ".agents",
    ".harness-factory/install-manifest.json", ".harness-factory",
])
def test_dependency_exception_does_not_allow_owned_or_control_links(installed, tmp_path, relative):
    _, target = installed
    dependency_link(target)
    owned = target / relative
    outside = tmp_path / "moved-owned"
    owned.rename(outside)
    owned.symlink_to(outside, target_is_directory=outside.is_dir())
    result = audit(target, tmp_path / "analysis")
    assert result.exit_code == 3
    assert not result.stdout.strip()
    assert "symlink" in result.stderr


@pytest.mark.parametrize("tamper,diagnostic", [
    ("generated", "modified"), ("ownership", "ownership"), ("control", "installer control"),
])
def test_dependency_exception_preserves_integrity_checks(installed, tmp_path, tamper, diagnostic):
    _, target = installed
    dependency_link(target)
    if tamper == "generated":
        (target / "AGENTS.md").write_text("# Modified generated instructions\n")
    elif tamper == "ownership":
        path = target / ".harness-factory/install-manifest.json"
        value = json.loads(path.read_text())
        value["files"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(value))
    else:
        (target / ".harness-factory/rogue.json").write_text("{}\n")
    result = audit(target, tmp_path / "analysis")
    assert result.exit_code == 2
    value = json.loads(result.stdout)
    assert value["status"] == "fail" and value["valid"] is False
    assert any(diagnostic in item for item in value["subjectDiagnostics"])


@pytest.mark.parametrize("directory", ["node_modules", ".venv"])
def test_standalone_generated_bundles_still_reject_dependency_links(installed, tmp_path, directory):
    project, _ = installed
    generated = project / "build/harness"
    assert generated.is_dir()
    dependency_link(generated, directory)
    result = audit(generated, tmp_path / "standalone-analysis")
    assert result.exit_code == 2
    assert any("symlink" in item for item in json.loads(result.stdout)["subjectDiagnostics"])
    with pytest.raises(HdpGenerationError, match="symlink"):
        package_release(generated, project / "harness/hdp.yaml", project / "harness/bindings/codex.yaml",
                        tmp_path / "release")
