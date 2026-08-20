import os
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import hdp.project as project_module
from hdp.cli import harness_main, main
from hdp.compiler import compile_hdp
from hdp.diagnostics import HdpInputError
from hdp.project import initialise_codex_sdlc, install_harness, resolve_project


def test_codex_template_builds_and_installs_with_dry_run() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()

        result = initialise_codex_sdlc(project)
        assert result["status"] == "initialized"
        paths = resolve_project(project)
        compilation = compile_hdp(paths.definition, paths.binding, paths.build)
        assert compilation.status == "pass"

        plan = install_harness(paths.build, target, dry_run=True)
        assert plan["status"] == "planned"
        assert not plan["conflicts"]
        assert not (target / "AGENTS.md").exists()

        installed = install_harness(paths.build, target, dry_run=False)
        assert installed["status"] == "installed"
        assert (target / "AGENTS.md").is_file()
        assert (target / ".harness-factory/install-manifest.json").is_file()

        repeated = install_harness(paths.build, target, dry_run=False)
        assert repeated["status"] == "installed"
        assert all(item["action"] == "unchanged" for item in repeated["actions"])


def test_install_refuses_unowned_or_locally_modified_file() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)

        agents = target / "AGENTS.md"
        agents.write_text("user-owned instructions\n", encoding="utf-8")
        result = install_harness(paths.build, target, dry_run=False)
        assert result["status"] == "conflict"
        assert {item["path"] for item in result["conflicts"]} == {"AGENTS.md"}
        assert agents.read_text(encoding="utf-8") == "user-owned instructions\n"
        assert not (target / ".harness-factory/install-manifest.json").exists()


def test_install_refuses_to_adopt_identical_unowned_file() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)
        agents = target / "AGENTS.md"
        agents.write_bytes((paths.build / "AGENTS.md").read_bytes())

        result = install_harness(paths.build, target, dry_run=False)

        assert result["status"] == "conflict"
        assert result["conflicts"] == [{
            "path": "AGENTS.md",
            "reason": "existing file is unowned, even if content is identical",
        }]
        assert not (target / ".harness-factory/install-manifest.json").exists()


def test_install_refuses_symlinked_management_directory() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        outside = root / "outside"
        target.mkdir()
        outside.mkdir()
        os.symlink(outside, target / ".harness-factory")
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)

        try:
            install_harness(paths.build, target, dry_run=False)
        except Exception as exc:
            assert "refuses" in str(exc) and "destination" in str(exc)
        else:
            raise AssertionError("symlinked management directory was accepted")
        assert list(outside.iterdir()) == []


def test_directory_relative_writer_never_follows_destination_parent_symlink() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        target = root / "target"
        outside = root / "outside"
        target.mkdir()
        outside.mkdir()
        os.symlink(outside, target / ".agents")
        root_fd = os.open(target, project_module._DIRECTORY_FLAGS)
        try:
            with pytest.raises(HdpInputError, match="unsafe destination parent"):
                project_module._atomic_write_at(
                    root_fd,
                    Path(".agents/AGENTS.md"),
                    b"instructions\n",
                    mode=0o644,
                    allowed_current={None},
                )
        finally:
            os.close(root_fd)
        assert list(outside.iterdir()) == []


def test_install_refuses_symlinked_generated_source_directory() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        outside = root / "outside"
        target.mkdir()
        outside.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)

        skill_source = paths.build / ".agents/skills/codex-ai-sdlc"
        moved = outside / "codex-ai-sdlc"
        skill_source.rename(moved)
        os.symlink(moved, skill_source)

        try:
            install_harness(paths.build, target, dry_run=False)
        except Exception as exc:
            assert "symlink source" in str(exc)
        else:
            raise AssertionError("symlinked generated source was accepted")
        assert list(target.iterdir()) == []


def test_install_fails_closed_on_stale_managed_file() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)
        first = install_harness(paths.build, target, dry_run=False)
        assert first["status"] == "installed"

        generated_manifest_path = paths.build / ".hdp/manifest.json"
        generated_manifest = json.loads(generated_manifest_path.read_text(encoding="utf-8"))
        stale = generated_manifest["artifacts"].pop()
        generated_manifest_path.write_text(
            json.dumps(generated_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = install_harness(paths.build, target, dry_run=False)
        assert result["status"] == "conflict"
        assert result["conflicts"] == [
            {
                "path": stale["path"],
                "reason": (
                    "previously managed file is no longer generated; remove it explicitly"
                ),
            }
        ]
        assert (target / stale["path"]).is_file()


def test_install_rolls_back_all_files_after_injected_write_failure() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)
        original_write = project_module._atomic_write_at
        calls = 0

        def fail_fourth_write(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("injected write failure")
            return original_write(*args, **kwargs)

        with patch.object(project_module, "_atomic_write_at", side_effect=fail_fourth_write):
            with pytest.raises(OSError, match="injected write failure"):
                install_harness(paths.build, target, dry_run=False)

        assert not (target / "AGENTS.md").exists()
        assert not (target / ".agents/skills/codex-ai-sdlc/SKILL.md").exists()
        assert not (target / ".harness-factory/install-manifest.json").exists()
        assert not (target / ".harness-factory/install-transaction.json").exists()


def test_install_never_replays_unexplained_preexisting_journal() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)
        journal = target / ".harness-factory/install-transaction.json"
        journal.parent.mkdir()
        malicious = b"#!/bin/sh\necho hostile\n"
        journal.write_text(json.dumps({
            "schemaVersion": "1",
            "kind": "HarnessInstallTransaction",
            "entries": [{
                "path": ".git/hooks/pre-commit",
                "newSha256": project_module._sha256_bytes(malicious),
                "original": {
                    "sha256": project_module._sha256_bytes(malicious),
                    "mode": 0o755,
                    "contentBase64": "IyEvYmluL3NoCmVjaG8gaG9zdGlsZQo=",
                },
            }],
        }), encoding="utf-8")

        preview = install_harness(paths.build, target, dry_run=True)
        assert preview["status"] == "conflict"
        assert "manual recovery" in preview["conflicts"][0]["reason"]
        with pytest.raises(HdpInputError, match="unfinished installation journal"):
            install_harness(paths.build, target, dry_run=False)
        assert not (target / ".git/hooks/pre-commit").exists()
        assert journal.is_file()


def test_install_refuses_oversized_preexisting_journal_without_reading_it() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)
        journal = target / ".harness-factory/install-transaction.json"
        journal.parent.mkdir()
        with journal.open("wb") as handle:
            handle.seek(64 * 1024 * 1024)
            handle.write(b"\0")

        started = time.monotonic()
        with pytest.raises(HdpInputError, match="unfinished installation journal"):
            install_harness(paths.build, target, dry_run=False)
        assert time.monotonic() - started < 2
        assert journal.stat().st_size > 64 * 1024 * 1024


def test_install_refuses_required_manifest_fifo_without_blocking() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)
        manifest = paths.build / ".hdp/manifest.json"
        manifest.unlink()
        os.mkfifo(manifest)

        started = time.monotonic()
        with pytest.raises(HdpInputError, match="non-regular"):
            install_harness(paths.build, target, dry_run=False)
        assert time.monotonic() - started < 2


def test_install_refuses_concurrent_installer() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()
        initialise_codex_sdlc(project)
        paths = resolve_project(project)
        compile_hdp(paths.definition, paths.binding, paths.build)

        with project_module._target_lock(target):
            with pytest.raises(HdpInputError, match="already in progress"):
                install_harness(paths.build, target, dry_run=False)


def test_simplified_cli_happy_path() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project = root / "project"
        target = root / "target"
        target.mkdir()

        assert main(["init", str(project), "--template", "codex-sdlc"]) == 0
        assert main(["build", str(project), "--json"]) == 0
        assert main(
            ["install", str(target), "--project", str(project), "--dry-run", "--json"]
        ) == 0
        assert main(["install", str(target), "--project", str(project)]) == 0
        assert main(["verify", str(project), "--json"]) == 0
        assert main(["doctor", "--json"]) == 0


def test_product_cli_exposes_only_the_simple_workflow() -> None:
    assert harness_main(["--help"]) == 0
    assert harness_main(["validate", "missing.yaml"]) != 0


def test_release_requires_subject_bound_evidence() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary) / "project"
        initialise_codex_sdlc(project)
        assert main(["build", str(project)]) == 0
        assert main(["release", str(project)]) == 2


def test_product_audit_requires_explicit_allow_partial() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "foreign"
        harness.mkdir()
        (harness / "AGENTS.md").write_text("Run the tests.\n", encoding="utf-8")

        assert harness_main(["audit", str(harness), "--output", str(root / "strict")]) == 2
        assert harness_main([
            "audit", str(harness), "--output", str(root / "partial"), "--allow-partial",
        ]) == 0
