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
