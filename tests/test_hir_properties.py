import copy
from pathlib import Path

from hypothesis import given, strategies as st

from hdp.io import canonical_json, load_document
from hdp.normalise import normalise_hdp


ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples/software-development/hdp.yaml"


def test_hir_is_target_neutral_and_all_relations_resolve() -> None:
    hir = normalise_hdp(load_document(EXAMPLE), binding_ref="bindings/codex.yaml")
    serialized = canonical_json(hir.canonical_dict())
    entity_ids = {item.id for item in hir.entities}

    assert ".codex/config.toml" not in serialized
    assert ".agents/skills" not in serialized
    assert all(item.source in entity_ids and item.target in entity_ids for item in hir.relations)
    assert set(hir.dimensions) == {
        "identity_outcomes", "execution_environment_sandbox", "tools_capabilities",
        "context_memory", "lifecycle_orchestration", "observability_replay",
        "verification_evaluation", "governance_security", "target_bindings_packaging",
    }


def test_normalisation_is_idempotent_for_canonical_semantics() -> None:
    definition = load_document(EXAMPLE)
    first = normalise_hdp(definition)
    second = normalise_hdp(first.canonical_semantics)
    assert first.digest() == second.digest()


@given(st.permutations(["metadata", "purpose", "runtime", "evaluation", "governance"]))
def test_source_digest_is_invariant_to_mapping_key_order(order: list[str]) -> None:
    source = load_document(EXAMPLE)
    reordered = {key: copy.deepcopy(source[key]) for key in order}
    reordered.update({key: value for key, value in source.items() if key not in reordered})
    assert normalise_hdp(source).source_digest == normalise_hdp(reordered).source_digest
