"""Target-neutral Harness Intermediate Representation."""

from __future__ import annotations

import hashlib
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .io import canonical_json


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EntityBase(FrozenModel):
    id: str
    kind: str
    label: str
    source_pointers: tuple[str, ...]


class Actor(EntityBase):
    kind: Literal["actor"] = "actor"
    objectives: tuple[str, ...] = ()
    responsibilities: tuple[str, ...] = ()
    prohibited_actions: tuple[str, ...] = ()


class TaskState(EntityBase):
    kind: Literal["task_state"] = "task_state"
    state_type: Literal["task_class", "workflow_state"]
    entry_criteria: tuple[str, ...] = ()
    exit_criteria: tuple[str, ...] = ()
    terminal: bool = False


class Capability(EntityBase):
    kind: Literal["capability"] = "capability"
    capability_type: str
    side_effects: str
    interface_ref: str | None = None


class ContextSource(EntityBase):
    kind: Literal["context_source"] = "context_source"
    authority: str
    classification: str
    freshness_policy: str


class Artifact(EntityBase):
    kind: Literal["artifact"] = "artifact"
    direction: Literal["input", "output", "evidence"]
    media_type: str
    classification: str
    required: bool


class Environment(EntityBase):
    kind: Literal["environment"] = "environment"
    constraints: tuple[str, ...] = ()
    runtime: str | None = None


class Policy(EntityBase):
    kind: Literal["policy"] = "policy"
    effect: Literal["allow", "deny", "approval", "obligation", "stop"]
    statement: str
    fail_closed: bool = True


class EvaluatorGate(EntityBase):
    kind: Literal["evaluator_gate"] = "evaluator_gate"
    method: str
    deterministic: bool
    independence: str


class EventMetric(EntityBase):
    kind: Literal["event_metric"] = "event_metric"
    record_type: Literal["event", "metric"]
    fields: tuple[str, ...] = ()
    redaction: str | None = None


class AdapterRef(EntityBase):
    kind: Literal["adapter_ref"] = "adapter_ref"
    adapter: str
    version: str
    binding_ref: str | None = None


Entity = Annotated[
    Union[
        Actor,
        TaskState,
        Capability,
        ContextSource,
        Artifact,
        Environment,
        Policy,
        EvaluatorGate,
        EventMetric,
        AdapterRef,
    ],
    Field(discriminator="kind"),
]


RelationType = Literal[
    "performs",
    "may_use",
    "requires",
    "consumes",
    "produces",
    "reads",
    "runs_in",
    "transitions_to",
    "governs",
    "checks",
    "observes",
    "realizes",
]


class Relation(FrozenModel):
    id: str
    relation: RelationType
    source: str
    target: str
    source_pointers: tuple[str, ...]
    constraints: tuple[str, ...] = ()


Dimension = Literal[
    "identity_outcomes",
    "execution_environment_sandbox",
    "tools_capabilities",
    "context_memory",
    "lifecycle_orchestration",
    "observability_replay",
    "verification_evaluation",
    "governance_security",
    "target_bindings_packaging",
]


class HIR(FrozenModel):
    hir_version: Literal["0.1.0"] = "0.1.0"
    source_hdp_version: str
    source_digest: str
    source_id: str
    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]
    dimensions: dict[Dimension, tuple[str, ...]]
    canonical_semantics: dict[str, Any]

    @model_validator(mode="after")
    def validate_graph(self) -> "HIR":
        identifiers = [entity.id for entity in self.entities]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("HIR entity IDs must be globally unique")
        entity_ids = set(identifiers)
        relation_ids: set[str] = set()
        for relation in self.relations:
            if relation.id in relation_ids:
                raise ValueError(f"duplicate HIR relation ID {relation.id!r}")
            relation_ids.add(relation.id)
            if relation.source not in entity_ids or relation.target not in entity_ids:
                raise ValueError(f"HIR relation {relation.id!r} has an unresolved endpoint")
        for dimension, members in self.dimensions.items():
            unknown = set(members) - entity_ids
            if unknown:
                raise ValueError(f"HIR dimension {dimension!r} references {sorted(unknown)!r}")
        return self

    def canonical_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    def digest(self) -> str:
        return hashlib.sha256(canonical_json(self.canonical_dict()).encode()).hexdigest()
