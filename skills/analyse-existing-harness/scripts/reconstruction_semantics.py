"""Self-contained semantic checks for reconstructed HDP documents.

The analysis skill can be installed without the ``hdp-reference`` Python
package.  Keep these checks deterministic and limited to the cross-field
contracts needed to reject broken references, trace graphs, and runtime
profiles.
"""

from collections import defaultdict
from pathlib import PurePosixPath
import re
from typing import Any, Iterable, Mapping, Sequence


RecordPath = tuple[str, ...]


COLLECTION_PATHS: tuple[RecordPath, ...] = (
    ("purpose", "targetUsers"),
    ("purpose", "intendedOutcomes"),
    ("operationalContext", "environments"),
    ("operationalContext", "taskDistribution"),
    ("operationalContext", "assumptions"),
    ("operationalContext", "dependencies"),
    ("operationalContext", "exclusions"),
    ("success", "measures"),
    ("success", "thresholds"),
    ("success", "acceptanceCriteria"),
    ("requirements",),
    ("models", "capabilityRequirements"),
    ("models", "providerConstraints"),
    ("contracts", "inputs"),
    ("contracts", "outputs"),
    ("contracts", "artifacts"),
    ("context", "constructionRules"),
    ("context", "knowledgeSources"),
    ("tools", "interfaces"),
    ("tools", "externalSystems"),
    ("orchestration", "roles"),
    ("orchestration", "stages"),
    ("governance", "dataClassifications"),
    ("governance", "approvals"),
    ("governance", "permissions", "prohibitedActions"),
    ("resources", "budgets"),
    ("resources", "timeouts"),
    ("resources", "rateLimits"),
    ("resources", "stoppingConditions"),
    ("failures", "taxonomy"),
    ("failures", "recoveryPolicies"),
    ("failures", "escalations"),
    ("observability", "events"),
    ("observability", "interventions"),
    ("safety", "securityControls"),
    ("safety", "privacyControls"),
    ("safety", "safetyConstraints"),
    ("safety", "compliance"),
    ("evaluation", "datasets"),
    ("evaluation", "fixtures"),
    ("evaluation", "scenarios"),
    ("evaluation", "metrics"),
    ("evaluation", "evaluators"),
    ("evaluation", "tests"),
    ("runtime", "deploymentTargets"),
    ("monitoring", "baselines"),
    ("monitoring", "driftRules"),
    ("monitoring", "alerts"),
    ("monitoring", "reassessmentTriggers"),
    ("evolution", "deprecations"),
    ("limitations",),
    ("risks",),
)


def _records(document: Mapping[str, Any], path: Sequence[str]) -> list[Mapping[str, Any]]:
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping):
            return []
        value = value.get(part, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _ids(document: Mapping[str, Any], path: RecordPath) -> set[str]:
    return {
        item["id"]
        for item in _records(document, path)
        if isinstance(item.get("id"), str)
    }


def _pointer(path: Sequence[str], index: int | None = None) -> str:
    parts = list(path)
    if index is not None:
        parts.append(str(index))
    return "/" + "/".join(parts)


def _values(record: Mapping[str, Any], field: str) -> Iterable[tuple[int | None, Any]]:
    value = record.get(field, [])
    if isinstance(value, list):
        return enumerate(value)
    return [(None, value)]


def _reference_messages(document: Mapping[str, Any]) -> list[str]:
    messages: list[str] = []
    locations: dict[str, list[str]] = defaultdict(list)
    for path in COLLECTION_PATHS:
        for index, record in enumerate(_records(document, path)):
            identifier = record.get("id")
            if isinstance(identifier, str):
                locations[identifier].append(f"{_pointer(path, index)}/id")
    for identifier, paths in sorted(locations.items()):
        if len(paths) > 1:
            messages.append(
                f"semantic {paths[1]}: stable id {identifier!r} is reused; first declared at {paths[0]}"
            )

    targets = {
        "measures": _ids(document, ("success", "measures")),
        "requirements": _ids(document, ("requirements",)),
        "outcomes": _ids(document, ("purpose", "intendedOutcomes")),
        "evaluators": _ids(document, ("evaluation", "evaluators")),
        "metrics": _ids(document, ("evaluation", "metrics")),
        "tests": _ids(document, ("evaluation", "tests")),
        "scenarios": _ids(document, ("evaluation", "scenarios")),
        "fixtures": _ids(document, ("evaluation", "fixtures")),
        "task_classes": _ids(document, ("operationalContext", "taskDistribution")),
        "roles": _ids(document, ("orchestration", "roles")),
        "stages": _ids(document, ("orchestration", "stages")),
        "tools": _ids(document, ("tools", "interfaces")),
        "failures": _ids(document, ("failures", "taxonomy")),
        "artifacts": _ids(document, ("contracts", "artifacts")),
    }

    checks: tuple[tuple[RecordPath, str, str], ...] = (
        (("purpose", "intendedOutcomes"), "measureIds", "measures"),
        (("success", "thresholds"), "measureId", "measures"),
        (("success", "acceptanceCriteria"), "requirementIds", "requirements"),
        (("success", "acceptanceCriteria"), "evaluatorIds", "evaluators"),
        (("requirements",), "verificationIds", "tests"),
        (("orchestration", "roles"), "toolIds", "tools"),
        (("orchestration", "stages"), "roleIds", "roles"),
        (("orchestration", "stages"), "next", "stages"),
        (("failures", "recoveryPolicies"), "failureIds", "failures"),
        (("safety", "securityControls"), "verificationIds", "tests"),
        (("safety", "privacyControls"), "verificationIds", "tests"),
        (("safety", "safetyConstraints"), "verificationIds", "tests"),
        (("evaluation", "scenarios"), "taskClassId", "task_classes"),
        (("evaluation", "scenarios"), "fixtureIds", "fixtures"),
        (("evaluation", "scenarios"), "expectedOutcomeIds", "outcomes"),
        (("evaluation", "metrics"), "measureId", "measures"),
        (("evaluation", "evaluators"), "metricIds", "metrics"),
        (("evaluation", "tests"), "evaluatorId", "evaluators"),
        (("evaluation", "tests"), "scenarioIds", "scenarios"),
        (("evaluation", "tests"), "requirementIds", "requirements"),
        (("evaluation", "tests"), "evidenceArtifactId", "artifacts"),
        (("evaluation", "negativeTests"), "testId", "tests"),
        (("evaluation", "adversarialTests"), "testId", "tests"),
        (("evaluation", "regressionTests"), "testId", "tests"),
        (("monitoring", "baselines"), "measureId", "measures"),
        (("monitoring", "driftRules"), "measureId", "measures"),
    )
    for path, field, target_name in checks:
        for index, record in enumerate(_records(document, path)):
            for subindex, value in _values(record, field):
                if value not in targets[target_name]:
                    suffix = f"/{subindex}" if subindex is not None else ""
                    messages.append(
                        f"semantic {_pointer(path, index)}/{field}{suffix}: "
                        f"{field} references unknown id {value!r}"
                    )

    allowed = (
        document.get("governance", {})
        .get("permissions", {})
        .get("tools", {})
        .get("allowedIds", [])
    )
    if isinstance(allowed, list):
        for index, value in enumerate(allowed):
            if value not in targets["tools"]:
                messages.append(
                    "semantic /governance/permissions/tools/allowedIds/"
                    f"{index}: allowedIds references unknown id {value!r}"
                )

    all_ids = set(locations)
    for index, record in enumerate(_records(document, ("evolution", "deprecations"))):
        target = record.get("targetId")
        if target not in all_ids:
            messages.append(
                f"semantic /evolution/deprecations/{index}/targetId: "
                f"targetId references unknown id {target!r}"
            )
    return messages


def _trace_messages(document: Mapping[str, Any]) -> list[str]:
    messages: list[str] = []
    nodes = _records(document, ("traceability", "nodes"))
    edges = _records(document, ("traceability", "edges"))
    node_locations: dict[str, list[str]] = defaultdict(list)
    for index, node in enumerate(nodes):
        if isinstance(node.get("id"), str):
            node_locations[node["id"]].append(f"/traceability/nodes/{index}/id")
    for identifier, paths in sorted(node_locations.items()):
        if len(paths) > 1:
            messages.append(
                f"semantic {paths[1]}: trace node id {identifier!r} is reused; first declared at {paths[0]}"
            )

    trace_targets = {
        "outcome": _ids(document, ("purpose", "intendedOutcomes")),
        "requirement": _ids(document, ("requirements",)),
        "component": _ids(document, ("contracts", "artifacts")),
        "test": _ids(document, ("evaluation", "tests")),
        "evidence": _ids(document, ("contracts", "artifacts")),
        "risk": _ids(document, ("risks",)),
        "control": (
            _ids(document, ("safety", "securityControls"))
            | _ids(document, ("safety", "privacyControls"))
            | _ids(document, ("safety", "safetyConstraints"))
        ),
    }
    for index, node in enumerate(nodes):
        kind = node.get("kind")
        if kind in trace_targets and node.get("ref") not in trace_targets[kind]:
            messages.append(
                f"semantic /traceability/nodes/{index}/ref: {kind} trace node "
                f"references unknown id {node.get('ref')!r}"
            )

    node_ids = set(node_locations)
    outgoing: dict[str, set[str]] = defaultdict(set)
    for index, edge in enumerate(edges):
        for field in ("from", "to"):
            value = edge.get(field)
            if value not in node_ids:
                messages.append(
                    f"semantic /traceability/edges/{index}/{field}: "
                    f"trace edge references unknown node {value!r}"
                )
        if isinstance(edge.get("from"), str) and isinstance(edge.get("to"), str):
            outgoing[edge["from"]].add(edge["to"])

    node_by_id = {node.get("id"): node for node in nodes}
    required_kinds = {"requirement", "component", "test", "evidence"}
    for node in nodes:
        if node.get("kind") != "outcome" or not isinstance(node.get("id"), str):
            continue
        frontier = [node["id"]]
        visited: set[str] = set()
        reached: set[str] = set()
        while frontier:
            current = frontier.pop()
            if current in visited:
                continue
            visited.add(current)
            kind = node_by_id.get(current, {}).get("kind")
            if kind in required_kinds:
                reached.add(kind)
            frontier.extend(sorted(outgoing.get(current, set()) - visited))
        missing = sorted(required_kinds - reached)
        if missing:
            messages.append(
                "semantic /traceability: outcome lacks trace path covering: "
                + ", ".join(missing)
            )
    return messages


def _profile_messages(document: Mapping[str, Any]) -> list[str]:
    profile = document.get("runtime", {}).get("profile")
    if not isinstance(profile, Mapping):
        return ["profile /runtime/profile: must be a mapping"]
    messages: list[str] = []
    identifier = profile.get("id")
    if not isinstance(identifier, str) or re.fullmatch(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", identifier) is None:
        messages.append("profile /runtime/profile/id: must be a lowercase hyphenated slug")
    if profile.get("type") not in {"codex-software-development", "agent-spec", "custom"}:
        messages.append("profile /runtime/profile/type: unsupported runtime profile type")
    version = profile.get("version")
    if not isinstance(version, str) or re.fullmatch(
        r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$",
        version,
    ) is None:
        messages.append("profile /runtime/profile/version: must be a semantic version")
    if profile.get("conformance") not in {
        "core", "development", "controlled", "production", "high-assurance"
    }:
        messages.append("profile /runtime/profile/conformance: unsupported conformance level")
    return messages


def _operational_messages(document: Mapping[str, Any]) -> list[str]:
    messages: list[str] = []
    permissions = document.get("governance", {}).get("permissions", {})
    filesystem = permissions.get("filesystem", {})
    read = {str(PurePosixPath(item)) for item in filesystem.get("read", [])}
    write = {str(PurePosixPath(item)) for item in filesystem.get("write", [])}
    for item in sorted(write - read):
        messages.append(
            f"semantic /governance/permissions/filesystem/write: writable path {item!r} must also be readable"
        )
    network = permissions.get("network", {})
    if network.get("allowed") is False and network.get("destinations"):
        messages.append(
            "semantic /governance/permissions/network: network destinations cannot be declared when network is denied"
        )

    evaluation = document.get("evaluation", {})
    for index, fixture in enumerate(evaluation.get("fixtures", [])):
        if fixture.get("visibility") == "hidden" and fixture.get("publicPath"):
            messages.append(
                f"semantic /evaluation/fixtures/{index}/publicPath: hidden fixtures cannot expose publicPath"
            )
    for index, evaluator in enumerate(evaluation.get("evaluators", [])):
        if evaluator.get("independence") == "self":
            messages.append(
                f"semantic /evaluation/evaluators/{index}/independence: acceptance evaluator must be independent"
            )
        if evaluator.get("method") == "llm-judge":
            for field in ("repetitions", "aggregation", "uncertainty"):
                if field not in evaluator:
                    messages.append(
                        f"semantic /evaluation/evaluators/{index}: LLM judge requires {field}"
                    )

    for index, requirement in enumerate(document.get("requirements", [])):
        if requirement.get("priority") == "must" and requirement.get("status") != "accepted":
            messages.append(
                f"semantic /requirements/{index}/status: MUST requirements must be accepted before generation"
            )
    budgets = document.get("resources", {}).get("budgets", [])
    if not any(item.get("resource") == "wall-time" and item.get("hard") for item in budgets):
        messages.append(
            "semantic /resources/budgets: at least one hard wall-time budget is required"
        )

    stages = document.get("orchestration", {}).get("stages", [])
    if stages and not any(not item.get("next") for item in stages):
        messages.append("semantic /orchestration/stages: orchestration requires a terminal stage")
    if stages:
        ids = [str(item.get("id")) for item in stages]
        adjacency = {
            str(item.get("id")): [str(target) for target in item.get("next", [])]
            for item in stages
        }
        reached: set[str] = set()
        frontier = [ids[0]]
        while frontier:
            current = frontier.pop()
            if current in reached:
                continue
            reached.add(current)
            frontier.extend(adjacency.get(current, []))
        for index, identifier in enumerate(ids):
            if identifier not in reached:
                messages.append(
                    f"semantic /orchestration/stages/{index}: stage {identifier!r} is unreachable"
                )

        visiting: set[str] = set()
        visited: set[str] = set()
        cyclic = False

        def visit(identifier: str) -> None:
            nonlocal cyclic
            if identifier in visiting:
                cyclic = True
                return
            if identifier in visited:
                return
            visiting.add(identifier)
            for target in adjacency.get(identifier, []):
                visit(target)
            visiting.remove(identifier)
            visited.add(identifier)

        for identifier in ids:
            visit(identifier)
        if cyclic:
            messages.append(
                "semantic /orchestration/stages: workflow cycles require an explicit bounded-loop construct"
            )
    return messages


def semantic_messages(document: Mapping[str, Any]) -> list[str]:
    """Return deterministic semantic diagnostics without project imports."""

    messages: list[str] = []
    messages.extend(_reference_messages(document))
    messages.extend(_trace_messages(document))
    messages.extend(_profile_messages(document))
    messages.extend(_operational_messages(document))
    return sorted(set(messages))
