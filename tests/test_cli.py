import tempfile
from pathlib import Path

from hdp.cli import main
from hdp.compiler import compile_hdp


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "software-development" / "hdp.yaml"
BINDING = ROOT / "examples" / "software-development" / "bindings" / "codex.yaml"


def test_validate_invalid_definition_exits_nonzero() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        invalid = Path(temporary) / "invalid.yaml"
        invalid.write_text("hdpVersion: 0.1.0\nkind: HarnessDefinition\n")
        assert main(["validate", str(invalid), "--json"]) == 2


def test_verify_release_missing_manifest_exits_nonzero() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        assert main(["verify-release", temporary]) == 2


def test_test_command_uses_trusted_definition_and_detects_tamper() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        harness = Path(temporary) / "harness"
        assert compile_hdp(EXAMPLE, BINDING, harness).status == "pass"

        command = [
            "test", str(harness), "--definition", str(EXAMPLE),
            "--binding", str(BINDING),
        ]
        assert main(command) == 0

        card = harness / "HarnessCard.md"
        card.write_text(card.read_text(encoding="utf-8") + "\nTAMPER\n", encoding="utf-8")
        assert main(command) == 2


def test_analyse_partial_result_requires_explicit_allow_partial() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        harness = root / "harness"
        harness.mkdir()
        (harness / "AGENTS.md").write_text("Run the tests.\n", encoding="utf-8")

        strict_output = root / "strict-analysis"
        assert main(["analyse", str(harness), "--output", str(strict_output)]) == 2
        assert (strict_output / "coverage-report.json").is_file()

        accepted_output = root / "accepted-analysis"
        assert main(
            [
                "analyse",
                str(harness),
                "--output",
                str(accepted_output),
                "--allow-partial",
            ]
        ) == 0
        assert (accepted_output / "uncertainty-report.json").is_file()
