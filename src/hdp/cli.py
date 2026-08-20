"""Typer command-line interface for the Harness Factory reference."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer

from .adapters import CodexAdapter
from . import __version__
from .analyser import analyse_harness
from .bindings import load_codex_binding
from .compiler import compare_hdp, compile_hdp, validate_and_normalise
from .conformance import stable_binding_identity
from .diagnostics import HdpError
from .io import atomic_write_text, dump_json, load_document
from .packaging import package_release, verify_release
from .project import (
    executable_status,
    initialise_codex_sdlc,
    install_harness,
    resolve_project,
)
from .schema_validation import structural_diagnostics
from .semantic_validation import semantic_diagnostics


app = typer.Typer(
    name="hdp",
    help="Compile, analyse, test, package, and verify target-specific AI harnesses.",
    no_args_is_help=True,
    add_completion=False,
)

harness_app = typer.Typer(
    name="harness",
    help="Create, install, audit, verify, and release AI harnesses.",
    no_args_is_help=True,
    add_completion=False,
)


def _emit(value: Any) -> None:
    typer.echo(json.dumps(value, indent=2, sort_keys=True))


def _fail(message: str, code: int = 3) -> None:
    typer.echo(f"ERROR: {message}", err=True)
    raise typer.Exit(code)


def _human_or_json(value: dict[str, Any], *, json_output: bool, message: str) -> None:
    if json_output:
        _emit(value)
    else:
        typer.echo(message)


@app.command("init")
def init_command(
    directory: Path = typer.Argument(Path("."), help="New HDP package directory."),
    template: str = typer.Option(
        "empty",
        "--template",
        help="Starter template: empty or codex-sdlc.",
    ),
) -> None:
    """Initialize a hybrid HDP package layout without inventing domain facts."""
    if template == "codex-sdlc":
        try:
            _emit(initialise_codex_sdlc(directory))
        except (HdpError, ValueError, OSError) as exc:
            _fail(str(exc))
        return
    if template != "empty":
        _fail("unknown template; choose 'empty' or 'codex-sdlc'")
    directory = directory.resolve()
    if directory.exists() and any(directory.iterdir()):
        _fail(f"initialization directory must be empty: {directory}")
    for relative in (
        "definitions", "modules/roles", "modules/workflows", "modules/evidence",
        "modules/recovery", "scripts", "fixtures", "evals", "bindings", "schemas",
    ):
        (directory / relative).mkdir(parents=True, exist_ok=True)
    starter = {
        "hdpVersion": "0.1.0",
        "kind": "HarnessDefinition",
        "metadata": {
            "id": "UNKNOWN-REQUIRED", "name": "UNKNOWN-REQUIRED",
            "title": "Unresolved harness definition", "version": "0.0.0", "status": "draft",
        },
    }
    binding = {
        "bindingVersion": "0.1.0", "kind": "TargetBinding", "target": "codex",
        "adapterVersion": "0.1.0",
        "settings": {
            "model": "UNKNOWN-REQUIRED", "reasoningEffort": "UNKNOWN-REQUIRED",
            "approvalPolicy": "UNKNOWN-REQUIRED", "sandboxMode": "UNKNOWN-REQUIRED",
        },
        "mcpServers": [],
    }
    atomic_write_text(directory / "hdp.json", dump_json(starter))
    atomic_write_text(directory / "bindings/codex.json", dump_json(binding))
    atomic_write_text(
        directory / "README.md",
        "# HDP package\n\nThe starter is intentionally incomplete. Replace every `UNKNOWN-REQUIRED` "
        "from authoritative evidence, then run `hdp validate hdp.json`.\n",
    )
    _emit({"status": "initialized-incomplete", "directory": str(directory)})


@app.command("build")
def build_command(
    project: Path = typer.Argument(Path("."), help="Harness project directory."),
    output: Optional[Path] = typer.Option(None, "--output"),
    force_generated: bool = typer.Option(False, "--force-generated"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Discover, validate, compile, and statically check a harness project."""
    try:
        paths = resolve_project(project)
        destination = output.resolve() if output else paths.build
        result = compile_hdp(
            paths.definition,
            paths.binding,
            destination,
            force_generated=force_generated,
        )
        value = result.model_dump(mode="json")
        _human_or_json(
            value,
            json_output=json_output,
            message=f"BUILT {destination} HIR sha256:{result.hir_digest}",
        )
        if result.status != "pass":
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("install")
def install_command(
    target: Path = typer.Argument(..., help="Repository that will receive the generated harness."),
    project: Path = typer.Option(Path("."), "--project"),
    harness: Optional[Path] = typer.Option(None, "--harness"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Safely install manifest-owned generated files into a target repository."""
    try:
        paths = resolve_project(project)
        source = harness.resolve() if harness else paths.build
        result = install_harness(source, target, dry_run=dry_run)
        verb = "PLANNED" if dry_run else "INSTALLED"
        _human_or_json(
            result,
            json_output=json_output,
            message=f"{verb} {len(result['actions'])} managed files into {result['target']}",
        )
        if result["conflicts"]:
            for conflict in result["conflicts"]:
                typer.echo(
                    f"CONFLICT {conflict['path']}: {conflict['reason']}", err=True
                )
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("audit")
def audit_command(
    harness: Path = typer.Argument(..., help="Existing harness or repository to inspect."),
    output: Optional[Path] = typer.Option(None, "--output"),
    allow_partial: bool = typer.Option(
        False,
        "--allow-partial",
        help="Exit successfully when the evidenced draft remains incomplete or invalid.",
    ),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Inventory a harness and fail closed unless its reconstructed HDP is valid."""
    resolved_harness = harness.resolve()
    destination = (
        output.resolve()
        if output
        else Path.cwd().resolve() / f"{resolved_harness.name}-analysis"
    )
    if destination == resolved_harness or resolved_harness in destination.parents:
        destination = resolved_harness.parent / f"{resolved_harness.name}-analysis"
    try:
        result = analyse_harness(resolved_harness, destination, allow_partial=True)
        _human_or_json(
            result,
            json_output=json_output,
            message=(
                f"AUDITED {resolved_harness}; valid={str(result['valid']).lower()} "
                f"evidence={result['evidenceRecords']} output={destination}"
            ),
        )
        if not result["valid"] and not allow_partial:
            typer.echo(
                "ERROR: reconstruction is partial or invalid; inspect the emitted "
                "coverage and uncertainty reports, or rerun with --allow-partial",
                err=True,
            )
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("verify")
def verify_project_command(
    project: Path = typer.Argument(Path("."), help="Harness project directory."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Rebuild a project and verify its generated harness against trusted inputs."""
    try:
        paths = resolve_project(project)
        result = compile_hdp(paths.definition, paths.binding, paths.build)
        binding_value = load_codex_binding(paths.binding)
        hir = validate_and_normalise(
            paths.definition, binding_ref=stable_binding_identity(binding_value)
        )
        conformance = CodexAdapter(binding_value).static_check(paths.build, hir)
        value = {
            "status": conformance.status,
            "hirDigest": result.hir_digest,
            "harness": str(paths.build),
            "checks": list(conformance.checks),
            "behaviouralConformance": "not-run",
        }
        _human_or_json(
            value,
            json_output=json_output,
            message=f"VERIFIED static harness conformance at {paths.build}",
        )
        if conformance.status != "pass":
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("release")
def release_project_command(
    project: Path = typer.Argument(Path("."), help="Harness project directory."),
    conformance: Optional[Path] = typer.Option(None, "--conformance"),
    output: Optional[Path] = typer.Option(None, "--output"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Create and verify an eligible release from subject-bound evidence."""
    try:
        paths = resolve_project(project)
        evidence = conformance.resolve() if conformance else paths.evidence
        destination = output.resolve() if output else paths.release
        if not evidence.is_file():
            _fail(
                f"subject-bound verification bundle is required: {evidence}", code=2
            )
        if not paths.build.is_dir():
            compile_hdp(paths.definition, paths.binding, paths.build)
        package_result = package_release(
            paths.build,
            paths.definition,
            paths.binding,
            destination,
            conformance=evidence,
        )
        verification = verify_release(destination)
        result = {"package": package_result, "verification": verification}
        eligible = bool(
            package_result.get("releaseEligible")
            and verification.get("verified")
            and verification.get("releaseEligible")
        )
        message = (
            f"RELEASED eligible verified payload at {destination}"
            if eligible
            else f"PACKAGED but NOT ELIGIBLE at {destination}"
        )
        _human_or_json(result, json_output=json_output, message=message)
        if not eligible:
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError, json.JSONDecodeError) as exc:
        _fail(str(exc))


@app.command("doctor")
def doctor_command(json_output: bool = typer.Option(False, "--json")) -> None:
    """Report local capabilities without reading credentials or changing configuration."""
    python_supported = sys.version_info[:2] == (3, 12)
    tools = [executable_status(name) for name in ("git", "uv", "codex", "docker")]
    result = {
        "status": "pass" if python_supported else "fail",
        "version": __version__,
        "python": {
            "version": ".".join(str(item) for item in sys.version_info[:3]),
            "supported": python_supported,
        },
        "tools": tools,
        "notes": {
            "codex": "required only for live behavioural evaluation",
            "docker": "optional external sandbox runner",
        },
    }
    _human_or_json(
        result,
        json_output=json_output,
        message=(
            f"DOCTOR {'PASS' if python_supported else 'FAIL'} Python "
            f"{result['python']['version']}; "
            + ", ".join(
                f"{item['name']}={'yes' if item['available'] else 'no'}" for item in tools
            )
        ),
    )
    if not python_supported:
        raise typer.Exit(2)


@app.command("validate")
def validate_command(
    definition: Path,
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run structural, semantic, and HIR invariant validation."""
    try:
        document = load_document(definition)
        diagnostics = structural_diagnostics(document)
        hir_digest = None
        if not diagnostics:
            diagnostics.extend(semantic_diagnostics(document, definition.parent))
        if not diagnostics:
            hir_digest = validate_and_normalise(definition).digest()
    except HdpError as exc:
        _fail(str(exc))
    result = {
        "valid": not diagnostics,
        "hirDigest": hir_digest,
        "diagnostics": [item.to_dict() for item in diagnostics],
    }
    if json_output:
        _emit(result)
    elif diagnostics:
        for item in diagnostics:
            typer.echo(f"{item.severity.upper()} {item.code} {item.instance_path or '/'}: {item.message}")
    else:
        typer.echo(f"VALID {definition} HIR sha256:{hir_digest}")
    if diagnostics:
        raise typer.Exit(2)


def _compile(definition: Path, binding: Path, output: Path, force_generated: bool) -> None:
    try:
        result = compile_hdp(definition, binding, output, force_generated=force_generated)
        _emit(result.model_dump(mode="json"))
        if result.status != "pass":
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("compile")
def compile_command(
    definition: Path,
    binding: Path = typer.Option(..., "--binding", help="Target binding YAML/JSON."),
    output: Path = typer.Option(..., "--output", help="Generated harness directory."),
    force_generated: bool = typer.Option(False, "--force-generated"),
) -> None:
    """Compile a valid HDP through the Codex adapter."""
    _compile(definition, binding, output, force_generated)


@app.command("generate", hidden=True)
def generate_alias(
    definition: Path,
    binding: Path = typer.Option(..., "--binding"),
    output: Path = typer.Option(..., "--output"),
    force_generated: bool = typer.Option(False, "--force-generated"),
) -> None:
    """Compatibility alias for compile."""
    _compile(definition, binding, output, force_generated)


def _analyse(harness: Path, output: Path, *, allow_partial: bool) -> None:
    try:
        result = analyse_harness(harness, output, allow_partial=True)
        _emit(result)
        if not result["valid"] and not allow_partial:
            typer.echo(
                "ERROR: reconstruction is partial or invalid; inspect the emitted "
                "coverage and uncertainty reports, or rerun with --allow-partial",
                err=True,
            )
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("analyse")
def analyse_command(
    harness: Path,
    output: Path = typer.Option(..., "--output"),
    allow_partial: bool = typer.Option(
        False,
        "--allow-partial",
        help="Exit successfully when the evidenced draft remains incomplete or invalid.",
    ),
) -> None:
    """Reconstruct an evidence-qualified draft HDP from a harness."""
    _analyse(harness, output, allow_partial=allow_partial)


@app.command("inspect", hidden=True)
def inspect_alias(
    harness: Path,
    output: Path = typer.Option(..., "--output"),
    allow_partial: bool = typer.Option(False, "--allow-partial"),
) -> None:
    """US spelling/inspection alias for analyse."""
    _analyse(harness, output, allow_partial=allow_partial)


@app.command("test")
def test_command(
    harness: Path,
    definition: Path = typer.Option(
        ..., "--definition", help="Trusted full source HDP used to verify the public harness."
    ),
    binding: Path = typer.Option(..., "--binding"),
) -> None:
    """Verify a generated harness against its trusted source and target binding."""
    try:
        binding_value = load_codex_binding(binding)
        hir = validate_and_normalise(
            definition, binding_ref=stable_binding_identity(binding_value)
        )
        result = CodexAdapter(binding_value).static_check(harness, hir)
        _emit(result.model_dump(mode="json"))
        if result.status != "pass":
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError, json.JSONDecodeError) as exc:
        _fail(str(exc))


@app.command("diff")
def diff_command(left: Path, right: Path) -> None:
    """Compare two HDPs by normalized target-neutral semantics."""
    try:
        result = compare_hdp(left, right)
        _emit(result)
        if not result["parity"]:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("package")
def package_command(
    harness: Path,
    definition: Path = typer.Option(..., "--definition"),
    binding: Path = typer.Option(..., "--binding"),
    output: Path = typer.Option(..., "--output"),
    conformance: Optional[Path] = typer.Option(
        None,
        "--conformance",
        help="Content-addressed verification-evidence bundle; gate results are derived.",
    ),
) -> None:
    """Create a deterministic local release and digest-only statements."""
    try:
        _emit(package_release(harness, definition, binding, output, conformance=conformance))
    except (HdpError, ValueError, OSError, json.JSONDecodeError) as exc:
        _fail(str(exc))


@app.command("verify-release")
def verify_release_command(release: Path) -> None:
    """Recompute a release payload and reject post-package tampering."""
    result = verify_release(release)
    _emit(result)
    if not result["verified"]:
        raise typer.Exit(2)


def main(argv: Optional[list[str]] = None) -> int:
    try:
        result = app(args=argv, prog_name="hdp", standalone_mode=False)
        return int(result) if isinstance(result, int) else 0
    except typer.Exit as exc:
        return int(exc.exit_code)
    except Exception as exc:  # Click usage and unexpected deterministic failures.
        typer.echo(f"ERROR: {exc}", err=True)
        return 3


def harness_main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the convention-driven product command."""

    try:
        result = harness_app(args=argv, prog_name="harness", standalone_mode=False)
        return int(result) if isinstance(result, int) else 0
    except typer.Exit as exc:
        return int(exc.exit_code)
    except Exception as exc:  # Click usage and unexpected deterministic failures.
        typer.echo(f"ERROR: {exc}", err=True)
        return 3


for _name, _command in (
    ("init", init_command),
    ("build", build_command),
    ("install", install_command),
    ("audit", audit_command),
    ("verify", verify_project_command),
    ("release", release_project_command),
    ("doctor", doctor_command),
):
    harness_app.command(_name)(_command)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
