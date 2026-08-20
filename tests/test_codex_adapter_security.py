import tempfile
from pathlib import Path

import pytest

from hdp.adapters import CodexAdapter
from hdp.bindings import load_codex_binding
from hdp.compiler import compile_hdp, validate_and_normalise
from hdp.conformance import stable_binding_identity
from hdp.diagnostics import HdpInputError
from hdp.io import dump_yaml, load_document


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/software-development/hdp.yaml"
BINDING = ROOT / "examples/software-development/bindings/codex.yaml"


def _write_yaml(root: Path, name: str, value: dict) -> Path:
    path = root / name
    path.write_text(dump_yaml(value), encoding="utf-8")
    return path


def test_command_bindings_cover_only_governance_allowed_commands() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        definition = load_document(EXAMPLE)
        definition["governance"]["permissions"]["tools"]["allowedIds"] = ["TOOL-PYTHON"]
        definition_path = _write_yaml(root, "hdp.yaml", definition)
        hir = validate_and_normalise(definition_path)

        restricted_binding = load_document(BINDING)
        restricted_binding["commandBindings"].pop("TOOL-GIT")
        binding_path = _write_yaml(root, "binding.yaml", restricted_binding)
        CodexAdapter(load_codex_binding(binding_path)).plan(hir)

        with pytest.raises(ValueError, match="unknown-or-denied=.*TOOL-GIT"):
            CodexAdapter(load_codex_binding(BINDING)).plan(hir)


def test_mcp_binding_and_unbound_protocol_capability_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        binding = load_document(BINDING)
        binding["mcpServers"] = [
            {
                "id": "example",
                "transport": "stdio",
                "command": "example-mcp",
                "enabledTools": ["read"],
            }
        ]
        binding_path = _write_yaml(root, "mcp-binding.yaml", binding)
        with pytest.raises(HdpInputError, match="rejects MCP configuration"):
            load_codex_binding(binding_path)

        definition = load_document(EXAMPLE)
        python_tool = next(
            item for item in definition["tools"]["interfaces"]
            if item["id"] == "TOOL-PYTHON"
        )
        python_tool["kind"] = "protocol"
        definition_path = _write_yaml(root, "mcp-hdp.yaml", definition)
        hir = validate_and_normalise(definition_path)
        command_only = load_document(BINDING)
        command_only["commandBindings"].pop("TOOL-PYTHON")
        command_binding_path = _write_yaml(root, "command-binding.yaml", command_only)
        with pytest.raises(ValueError, match="exactly cover governance-allowed"):
            CodexAdapter(load_codex_binding(command_binding_path)).plan(hir)


def test_missing_external_control_binding_fails_static_conformance() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        binding = load_document(BINDING)
        binding["externallyEnforcedResources"].remove("wall-time")
        binding_path = _write_yaml(root, "binding.yaml", binding)
        with pytest.raises(ValueError, match="missing=.*wall-time"):
            compile_hdp(EXAMPLE, binding_path, root / "generated")


@pytest.mark.parametrize(
    ("relative", "mutate", "check_id"),
    [
        (
            ".codex/config.toml",
            lambda path: path.write_text(path.read_text() + "# tamper\n"),
            "config-exact",
        ),
        (
            ".hdp/hir.json",
            lambda path: path.write_text(
                path.read_text().replace('"source_digest": "', '"source_digest": "0')
            ),
            "hir-exact",
        ),
        (
            ".hdp/manifest.json",
            lambda path: path.write_text(
                path.read_text().replace(
                    '"id": "urn:hdp:example:ai-sdlc"',
                    '"id": "urn:hdp:example:tampered"',
                )
            ),
            "manifest-exact",
        ),
    ],
)
def test_static_check_reports_config_hir_and_manifest_tamper(
    relative: str, mutate, check_id: str
) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        output = root / "generated"
        result = compile_hdp(EXAMPLE, BINDING, output)
        assert result.status == "pass"
        mutate(output / relative)

        binding = load_codex_binding(BINDING)
        hir = validate_and_normalise(
            EXAMPLE, binding_ref=stable_binding_identity(binding)
        )
        conformance = CodexAdapter(binding).static_check(output, hir)
        assert conformance.status == "fail"
        check = next(item for item in conformance.checks if item["id"] == check_id)
        assert check["passed"] is False


def test_compiled_hir_uses_same_declared_source_without_private_case_material() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "generated"
        result = compile_hdp(EXAMPLE, BINDING, output)
        assert result.status == "pass"
        public = load_document(output / ".hdp/source-definition.public.json")
        hir = load_document(output / ".hdp/hir.json")
        assert hir["canonical_semantics"] == public
        generated_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in output.rglob("*") if path.is_file()
        )
        assert "HDP_PRIVATE_CANARY_8F5C2E71" not in generated_text
        assert "reference/evaluator" not in generated_text
