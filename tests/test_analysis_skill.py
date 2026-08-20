from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "analyse-existing-harness" / "SKILL.md"


def test_analysis_skill_keeps_lossless_mapping_guards() -> None:
    text = SKILL.read_text(encoding="utf-8")

    required_guards = (
        "artifact mapping does not replace the output contract",
        "fixture `commitment`",
        "`safety.securityControls`, `safety.privacyControls`, and",
        "surfaces such as MCP or A2A map to `protocol`",
        "as one complete `reassessmentTriggers[].statement`",
        "first remaining alphabetic",
        "exact atomic value governed by the selected field",
        "exact subject-and-copula frame",
    )

    for guard in required_guards:
        assert guard in text


def test_analysis_skill_keeps_honest_incompleteness_gate() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "omit that field, retain the structural diagnostic" in text
    assert "blocking unknowns MUST" in text
    assert "set `generationReady: false`" in text
