"""Typer command-line interface for the Harness Factory reference."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import typer

from .adapters import CodexAdapter
from .analyser import analyse_harness
from .bindings import load_codex_binding
from .compiler import compare_hdp, compile_hdp, validate_and_normalise
from .conformance import stable_binding_identity
from .diagnostics import HdpError
from .io import atomic_write_text, dump_json, load_document
from .packaging import package_release, verify_release
from .schema_validation import structural_diagnostics
from .semantic_validation import semantic_diagnostics


app = typer.Typer(
    name="hdp",
    help="Compile, analyse, test, package, and verify target-specific AI harnesses.",
    no_args_is_help=True,
    add_completion=False,
)


def _emit(value: Any) -> None:
    typer.echo(json.dumps(value, indent=2, sort_keys=True))


def _fail(message: str, code: int = 3) -> None:
    typer.echo(f"ERROR: {message}", err=True)
    raise typer.Exit(code)


@app.command("init")
def init_command(
    directory: Path = typer.Argument(Path("."), help="New HDP package directory."),
) -> None:
    """Initialize a hybrid HDP package layout without inventing domain facts."""
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


def _analyse(harness: Path, output: Path) -> None:
    try:
        _emit(analyse_harness(harness, output, allow_partial=True))
    except (HdpError, ValueError, OSError) as exc:
        _fail(str(exc))


@app.command("analyse")
def analyse_command(
    harness: Path,
    output: Path = typer.Option(..., "--output"),
) -> None:
    """Reconstruct an evidence-qualified draft HDP from a harness."""
    _analyse(harness, output)


@app.command("inspect", hidden=True)
def inspect_alias(
    harness: Path,
    output: Path = typer.Option(..., "--output"),
) -> None:
    """US spelling/inspection alias for analyse."""
    _analyse(harness, output)


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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
