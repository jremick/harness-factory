"""Deterministically normalize a resolved HDP document into HIR."""

from __future__ import annotations

import hashlib
from pathlib import PurePath
from typing import Any, Iterable

from .hir import (
    Actor,
    AdapterRef,
    Artifact,
    Capability,
    ContextSource,
    Entity,
    Environment,
    EvaluatorGate,
    EventMetric,
    HIR,
    Policy,
    Relation,
    TaskState,
)
from .io import canonical_json


def _pointer(*parts: object) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _label(item: dict[str, Any]) -> str:
    return str(item.get("name") or item.get("title") or item.get("statement") or item["id"])


def normalise_hdp(document: dict[str, Any], *, binding_ref: str | None = None) -> HIR:
    if binding_ref is not None and (
        PurePath(binding_ref).is_absolute() or binding_ref.startswith(("file:", "~"))
    ):
        raise ValueError(
            "binding_ref must be a stable logical or content identity, not a machine-local path"
        )
    entities: list[Entity] = []
    relations: list[Relation] = []
    dimensions: dict[str, list[str]] = {
        "identity_outcomes": [],
        "execution_environment_sandbox": [],
        "tools_capabilities": [],
        "context_memory": [],
        "lifecycle_orchestration": [],
        "observability_replay": [],
        "verification_evaluation": [],
        "governance_security": [],
        "target_bindings_packaging": [],
    }

    def add(entity: Entity, *groups: str) -> None:
        entities.append(entity)
        for group in groups:
            dimensions[group].append(entity.id)

    roles = document["orchestration"]["roles"]
    for index, role in enumerate(roles):
        add(
            Actor(
                id=role["id"], label=_label(role),
                objectives=tuple(role.get("objectives", [])),
                responsibilities=tuple(role.get("responsibilities", [])),
                prohibited_actions=tuple(role.get("prohibitedActions", [])),
                source_pointers=(_pointer("orchestration", "roles", index),),
            ),
            "identity_outcomes", "lifecycle_orchestration",
        )

    task_ids: set[str] = set()
    for index, task in enumerate(document["operationalContext"].get("taskDistribution", [])):
        add(
            TaskState(
                id=task["id"], label=_label(task), state_type="task_class",
                exit_criteria=(), terminal=False,
                source_pointers=(_pointer("operationalContext", "taskDistribution", index),),
            ),
            "identity_outcomes", "lifecycle_orchestration",
        )
        task_ids.add(task["id"])
    for index, stage in enumerate(document["orchestration"].get("stages", [])):
        add(
            TaskState(
                id=stage["id"], label=_label(stage), state_type="workflow_state",
                entry_criteria=tuple(stage.get("entryCriteria", [])),
                exit_criteria=tuple(stage.get("exitCriteria", [])),
                terminal=not bool(stage.get("next")),
                source_pointers=(_pointer("orchestration", "stages", index),),
            ),
            "lifecycle_orchestration",
        )
        for role_id in stage.get("roleIds", []):
            relations.append(Relation(
                id=f"rel:{role_id}:performs:{stage['id']}", relation="performs",
                source=role_id, target=stage["id"],
                source_pointers=(_pointer("orchestration", "stages", index, "roleIds"),),
            ))
        for target in stage.get("next", []):
            relations.append(Relation(
                id=f"rel:{stage['id']}:transitions_to:{target}", relation="transitions_to",
                source=stage["id"], target=target,
                source_pointers=(_pointer("orchestration", "stages", index, "next"),),
            ))

    capabilities: set[str] = set()
    for index, tool in enumerate(document["tools"].get("interfaces", [])):
        add(
            Capability(
                id=tool["id"], label=_label(tool), capability_type=tool["kind"],
                side_effects=tool["sideEffects"], interface_ref=tool.get("interfaceRef"),
                source_pointers=(_pointer("tools", "interfaces", index),),
            ),
            "tools_capabilities",
        )
        capabilities.add(tool["id"])
    for role_index, role in enumerate(roles):
        for tool_id in role.get("toolIds", []):
            relations.append(Relation(
                id=f"rel:{role['id']}:may_use:{tool_id}", relation="may_use",
                source=role["id"], target=tool_id,
                source_pointers=(_pointer("orchestration", "roles", role_index, "toolIds"),),
            ))

    for index, source in enumerate(document["context"].get("knowledgeSources", [])):
        add(
            ContextSource(
                id=source["id"], label=_label(source), authority=source["authority"],
                classification=source["classification"],
                freshness_policy=source["freshnessPolicy"],
                source_pointers=(_pointer("context", "knowledgeSources", index),),
            ),
            "context_memory",
        )

    for direction, collection in (("input", "inputs"), ("output", "outputs"), ("evidence", "artifacts")):
        for index, artifact in enumerate(document["contracts"].get(collection, [])):
            add(
                Artifact(
                    id=artifact["id"], label=_label(artifact), direction=direction,
                    media_type=artifact["mediaType"], classification=artifact["classification"],
                    required=artifact["required"],
                    source_pointers=(_pointer("contracts", collection, index),),
                ),
                "identity_outcomes", "verification_evaluation",
            )

    for index, environment in enumerate(document["operationalContext"].get("environments", [])):
        add(
            Environment(
                id=environment["id"], label=_label(environment),
                constraints=tuple(environment.get("constraints", [])),
                source_pointers=(_pointer("operationalContext", "environments", index),),
            ),
            "execution_environment_sandbox",
        )

    permissions = document["governance"]["permissions"]
    add(
        Policy(
            id="POLICY-DEFAULT-DENY", label="Default-deny capability policy",
            effect="deny", statement="Capabilities are denied unless explicitly allowed.",
            source_pointers=("/governance/permissions/default",),
        ),
        "governance_security",
    )
    for index, item in enumerate(permissions.get("prohibitedActions", [])):
        add(
            Policy(
                id=item["id"], label=item["action"], effect="deny", statement=item["reason"],
                source_pointers=(_pointer("governance", "permissions", "prohibitedActions", index),),
            ),
            "governance_security",
        )
    for index, item in enumerate(document["governance"].get("approvals", [])):
        add(
            Policy(
                id=item["id"], label=item["trigger"], effect="approval",
                statement=f"Approval by {item['approver']} is required: {item['trigger']}",
                fail_closed=item["failClosed"],
                source_pointers=(_pointer("governance", "approvals", index),),
            ),
            "governance_security",
        )
    for index, item in enumerate(document["resources"].get("stoppingConditions", [])):
        add(
            Policy(
                id=item["id"], label=item["statement"], effect="stop",
                statement=item["statement"],
                source_pointers=(_pointer("resources", "stoppingConditions", index),),
            ),
            "lifecycle_orchestration", "governance_security",
        )

    for index, evaluator in enumerate(document["evaluation"].get("evaluators", [])):
        add(
            EvaluatorGate(
                id=evaluator["id"], label=_label(evaluator), method=evaluator["method"],
                deterministic=evaluator["method"] == "deterministic",
                independence=evaluator["independence"],
                source_pointers=(_pointer("evaluation", "evaluators", index),),
            ),
            "verification_evaluation",
        )
    for index, event in enumerate(document["observability"].get("events", [])):
        add(
            EventMetric(
                id=event["id"], label=_label(event), record_type="event",
                fields=tuple(event.get("fields", [])),
                redaction=document["observability"]["trace"].get("redaction"),
                source_pointers=(_pointer("observability", "events", index),),
            ),
            "observability_replay",
        )
    for index, metric in enumerate(document["evaluation"].get("metrics", [])):
        add(
            EventMetric(
                id=metric["id"], label=_label(metric), record_type="metric",
                source_pointers=(_pointer("evaluation", "metrics", index),),
            ),
            "observability_replay", "verification_evaluation",
        )

    profile = document["runtime"]["profile"]
    adapter_id = f"ADAPTER-{profile['id'].upper()}"
    add(
        AdapterRef(
            id=adapter_id, label=f"{profile['type']} target adapter",
            adapter=profile["type"], version=profile["version"], binding_ref=binding_ref,
            source_pointers=("/runtime/profile",),
        ),
        "target_bindings_packaging",
    )
    for entity in list(entities):
        if entity.id != adapter_id:
            relations.append(Relation(
                id=f"rel:{adapter_id}:realizes:{entity.id}", relation="realizes",
                source=adapter_id, target=entity.id, source_pointers=("/runtime/profile",),
            ))

    source_digest = hashlib.sha256(canonical_json(document).encode()).hexdigest()
    return HIR(
        source_hdp_version=document["hdpVersion"], source_digest=source_digest,
        source_id=document["metadata"]["id"],
        entities=tuple(sorted(entities, key=lambda item: (item.kind, item.id))),
        relations=tuple(sorted(relations, key=lambda item: item.id)),
        dimensions={key: tuple(sorted(value)) for key, value in sorted(dimensions.items())},
        canonical_semantics=document,
    )
