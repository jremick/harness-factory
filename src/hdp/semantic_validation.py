"""Cross-field semantic validation that JSON Schema cannot express."""

from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from .diagnostics import Diagnostic


_CONTROLLED_PROFILES = {"controlled", "production", "high-assurance"}
_SUPPORTED_EXTENSIONS = {"x-hdp-reconstruction"}


def _records(document: Mapping[str, Any], path: Sequence[str]) -> List[Mapping[str, Any]]:
    value: Any = document
    for part in path:
        if not isinstance(value, Mapping):
            return []
        value = value.get(part, [])
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _ids(records: Iterable[Mapping[str, Any]]) -> Set[str]:
    return {str(item["id"]) for item in records if "id" in item}


def _diag(code: str, message: str, path: str, rule: str, *related: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        instance_path=path,
        rule_id=rule,
        related_paths=list(related),
    )


def _check_unique_ids(document: Mapping[str, Any]) -> List[Diagnostic]:
    collections: List[Tuple[Sequence[str], List[Mapping[str, Any]]]] = []
    paths = [
        ("purpose", "targetUsers"), ("purpose", "intendedOutcomes"),
        ("operationalContext", "environments"), ("operationalContext", "taskDistribution"),
        ("operationalContext", "assumptions"), ("operationalContext", "dependencies"),
        ("operationalContext", "exclusions"), ("success", "measures"),
        ("success", "thresholds"), ("success", "acceptanceCriteria"),
        ("requirements",), ("models", "capabilityRequirements"),
        ("contracts", "inputs"), ("contracts", "outputs"), ("contracts", "artifacts"),
        ("context", "constructionRules"), ("context", "knowledgeSources"),
        ("tools", "interfaces"), ("tools", "externalSystems"),
        ("orchestration", "roles"), ("orchestration", "stages"),
        ("governance", "dataClassifications"), ("governance", "approvals"),
        ("resources", "budgets"), ("resources", "timeouts"),
        ("resources", "rateLimits"), ("resources", "stoppingConditions"),
        ("failures", "taxonomy"), ("failures", "recoveryPolicies"),
        ("failures", "escalations"), ("observability", "events"),
        ("observability", "interventions"), ("safety", "securityControls"),
        ("safety", "privacyControls"), ("safety", "safetyConstraints"),
        ("safety", "compliance"), ("evaluation", "datasets"),
        ("evaluation", "fixtures"), ("evaluation", "scenarios"),
        ("evaluation", "metrics"), ("evaluation", "evaluators"),
        ("evaluation", "tests"), ("runtime", "deploymentTargets"),
        ("monitoring", "baselines"), ("monitoring", "driftRules"),
        ("monitoring", "alerts"), ("monitoring", "reassessmentTriggers"),
        ("traceability", "nodes"), ("traceability", "edges"),
        ("evolution", "deprecations"), ("limitations",), ("risks",),
    ]
    seen: Dict[str, str] = {}
    diagnostics: List[Diagnostic] = []
    for path in paths:
        records = _records(document, path)
        collections.append((path, records))
        for index, record in enumerate(records):
            identifier = record.get("id")
            if not isinstance(identifier, str):
                continue
            pointer = "/" + "/".join(path) + f"/{index}/id"
            if identifier in seen:
                diagnostics.append(
                    _diag(
                        "HDP-SEM-DUPLICATE-ID",
                        f"stable id {identifier!r} is reused",
                        pointer,
                        "SEM-001",
                        seen[identifier],
                    )
                )
            else:
                seen[identifier] = pointer
    return diagnostics


def _check_refs(document: Mapping[str, Any]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []

    def require(
        records: List[Mapping[str, Any]], field: str, targets: Set[str], base: str, rule: str
    ) -> None:
        for index, record in enumerate(records):
            values = record.get(field, [])
            if not isinstance(values, list):
                values = [values]
            for subindex, value in enumerate(values):
                if value not in targets:
                    diagnostics.append(
                        _diag(
                            "HDP-SEM-UNRESOLVED-REF",
                            f"{field} references unknown id {value!r}",
                            f"{base}/{index}/{field}/{subindex}",
                            rule,
                        )
                    )

    measures = _ids(_records(document, ("success", "measures")))
    requirements = _ids(_records(document, ("requirements",)))
    outcomes = _ids(_records(document, ("purpose", "intendedOutcomes")))
    evaluators = _ids(_records(document, ("evaluation", "evaluators")))
    metrics = _ids(_records(document, ("evaluation", "metrics")))
    tests = _ids(_records(document, ("evaluation", "tests")))
    scenarios = _ids(_records(document, ("evaluation", "scenarios")))
    fixtures = _ids(_records(document, ("evaluation", "fixtures")))
    task_classes = _ids(_records(document, ("operationalContext", "taskDistribution")))
    roles = _ids(_records(document, ("orchestration", "roles")))
    stages = _ids(_records(document, ("orchestration", "stages")))
    tools = _ids(_records(document, ("tools", "interfaces")))
    failures = _ids(_records(document, ("failures", "taxonomy")))
    artifacts = _ids(_records(document, ("contracts", "artifacts")))

    require(_records(document, ("purpose", "intendedOutcomes")), "measureIds", measures, "/purpose/intendedOutcomes", "SEM-010")
    require(_records(document, ("success", "thresholds")), "measureId", measures, "/success/thresholds", "SEM-011")
    require(_records(document, ("success", "acceptanceCriteria")), "requirementIds", requirements, "/success/acceptanceCriteria", "SEM-012")
    require(_records(document, ("success", "acceptanceCriteria")), "evaluatorIds", evaluators, "/success/acceptanceCriteria", "SEM-013")
    require(_records(document, ("requirements",)), "verificationIds", tests, "/requirements", "SEM-014")
    require(_records(document, ("orchestration", "roles")), "toolIds", tools, "/orchestration/roles", "SEM-015")
    require(_records(document, ("orchestration", "stages")), "roleIds", roles, "/orchestration/stages", "SEM-016")
    require(_records(document, ("orchestration", "stages")), "next", stages, "/orchestration/stages", "SEM-017")
    require(_records(document, ("failures", "recoveryPolicies")), "failureIds", failures, "/failures/recoveryPolicies", "SEM-018")
    require(_records(document, ("evaluation", "scenarios")), "taskClassId", task_classes, "/evaluation/scenarios", "SEM-019")
    require(_records(document, ("evaluation", "scenarios")), "fixtureIds", fixtures, "/evaluation/scenarios", "SEM-020")
    require(_records(document, ("evaluation", "scenarios")), "expectedOutcomeIds", outcomes, "/evaluation/scenarios", "SEM-021")
    require(_records(document, ("evaluation", "metrics")), "measureId", measures, "/evaluation/metrics", "SEM-022")
    require(_records(document, ("evaluation", "evaluators")), "metricIds", metrics, "/evaluation/evaluators", "SEM-023")
    require(_records(document, ("evaluation", "tests")), "evaluatorId", evaluators, "/evaluation/tests", "SEM-024")
    require(_records(document, ("evaluation", "tests")), "scenarioIds", scenarios, "/evaluation/tests", "SEM-025")
    require(_records(document, ("evaluation", "tests")), "requirementIds", requirements, "/evaluation/tests", "SEM-026")
    require(_records(document, ("evaluation", "tests")), "evidenceArtifactId", artifacts, "/evaluation/tests", "SEM-027")
    for field in ("negativeTests", "adversarialTests", "regressionTests"):
        require(_records(document, ("evaluation", field)), "testId", tests, f"/evaluation/{field}", "SEM-028")
    allowed_tool_ids = (
        document.get("governance", {})
        .get("permissions", {})
        .get("tools", {})
        .get("allowedIds", [])
    )
    for index, tool_id in enumerate(allowed_tool_ids):
        if tool_id not in tools:
            diagnostics.append(
                _diag(
                    "HDP-SEM-UNRESOLVED-REF",
                    f"allowedIds references unknown id {tool_id!r}",
                    f"/governance/permissions/tools/allowedIds/{index}",
                    "SEM-029",
                )
            )
    require(_records(document, ("monitoring", "baselines")), "measureId", measures, "/monitoring/baselines", "SEM-032")
    require(_records(document, ("monitoring", "driftRules")), "measureId", measures, "/monitoring/driftRules", "SEM-033")
    return diagnostics


def _check_permission_paths(document: Mapping[str, Any]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    permissions = document.get("governance", {}).get("permissions", {})
    filesystem = permissions.get("filesystem", {})
    read = {str(PurePosixPath(item)) for item in filesystem.get("read", [])}
    write = {str(PurePosixPath(item)) for item in filesystem.get("write", [])}
    for item in sorted(write - read):
        diagnostics.append(
            _diag(
                "HDP-SEM-WRITE-NOT-READABLE",
                f"writable path {item!r} must also be readable",
                "/governance/permissions/filesystem/write",
                "SEM-030",
            )
        )
    network = permissions.get("network", {})
    if network.get("allowed") is False and network.get("destinations"):
        diagnostics.append(
            _diag(
                "HDP-SEM-NETWORK-CONTRADICTION",
                "network destinations cannot be declared when network is denied",
                "/governance/permissions/network",
                "SEM-031",
            )
        )
    return diagnostics


def _check_evaluation(document: Mapping[str, Any]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    evaluation = document.get("evaluation", {})
    for index, fixture in enumerate(evaluation.get("fixtures", [])):
        if fixture.get("visibility") == "hidden" and fixture.get("publicPath"):
            diagnostics.append(
                _diag(
                    "HDP-SEM-HIDDEN-FIXTURE-LEAK",
                    "hidden fixtures cannot expose publicPath",
                    f"/evaluation/fixtures/{index}/publicPath",
                    "SEM-040",
                )
            )
    for index, evaluator in enumerate(evaluation.get("evaluators", [])):
        if evaluator.get("independence") == "self":
            diagnostics.append(
                _diag(
                    "HDP-SEM-EVALUATOR-NOT-INDEPENDENT",
                    "acceptance evaluators must be external or independently operated",
                    f"/evaluation/evaluators/{index}/independence",
                    "SEM-041",
                )
            )
        if evaluator.get("method") == "llm-judge":
            for field in ("repetitions", "aggregation", "uncertainty"):
                if field not in evaluator:
                    diagnostics.append(
                        _diag(
                            "HDP-SEM-LLM-JUDGE-INCOMPLETE",
                            f"LLM judge requires {field}",
                            f"/evaluation/evaluators/{index}",
                            "SEM-042",
                        )
                    )
    return diagnostics


def _check_generation_completeness(document: Mapping[str, Any]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    for index, requirement in enumerate(document.get("requirements", [])):
        if requirement.get("priority") == "must" and not requirement.get("verificationIds"):
            diagnostics.append(
                _diag(
                    "HDP-SEM-MUST-NOT-VERIFIED",
                    "MUST requirements require at least one verification test",
                    f"/requirements/{index}/verificationIds",
                    "SEM-055",
                )
            )
        if requirement.get("priority") == "must" and requirement.get("status") != "accepted":
            diagnostics.append(
                _diag(
                    "HDP-SEM-UNRESOLVED-MUST",
                    "MUST requirements must be accepted before generation",
                    f"/requirements/{index}/status",
                    "SEM-050",
                )
            )
    budgets = document.get("resources", {}).get("budgets", [])
    if not any(item.get("resource") == "wall-time" and item.get("hard") for item in budgets):
        diagnostics.append(
            _diag(
                "HDP-SEM-NO-HARD-WALLTIME",
                "at least one hard wall-time budget is required",
                "/resources/budgets",
                "SEM-051",
            )
        )
    stages = document.get("orchestration", {}).get("stages", [])
    if stages and not any(not item.get("next") for item in stages):
        diagnostics.append(
            _diag(
                "HDP-SEM-NO-TERMINAL-STAGE",
                "orchestration requires at least one terminal stage",
                "/orchestration/stages",
                "SEM-052",
            )
        )
    return diagnostics


def _check_profile_obligations(document: Mapping[str, Any]) -> List[Diagnostic]:
    """Enforce cumulative obligations selected by the conformance profile."""

    conformance = (
        document.get("runtime", {}).get("profile", {}).get("conformance")
    )
    if conformance not in _CONTROLLED_PROFILES:
        return []

    diagnostics: List[Diagnostic] = []
    evaluation = document.get("evaluation", {})
    for field in ("negativeTests", "adversarialTests", "regressionTests"):
        if not evaluation.get(field):
            diagnostics.append(
                _diag(
                    "HDP-SEM-PROFILE-OBLIGATION",
                    f"{conformance} conformance requires at least one {field} entry",
                    f"/evaluation/{field}",
                    "SEM-070",
                )
            )
    evaluators = evaluation.get("evaluators", [])
    if not any(item.get("independence") == "external" for item in evaluators):
        diagnostics.append(
            _diag(
                "HDP-SEM-PROFILE-OBLIGATION",
                f"{conformance} conformance requires an external evaluator",
                "/evaluation/evaluators",
                "SEM-071",
            )
        )
    permissions = document.get("governance", {}).get("permissions", {})
    if permissions.get("default") != "deny":
        diagnostics.append(
            _diag(
                "HDP-SEM-PROFILE-OBLIGATION",
                f"{conformance} conformance requires deny-by-default permissions",
                "/governance/permissions/default",
                "SEM-072",
            )
        )
    if not document.get("monitoring", {}).get("driftRules"):
        diagnostics.append(
            _diag(
                "HDP-SEM-PROFILE-OBLIGATION",
                f"{conformance} conformance requires at least one drift rule",
                "/monitoring/driftRules",
                "SEM-073",
            )
        )
    return diagnostics


def _check_extensions(document: Mapping[str, Any]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    extensions = document.get("extensions", {})
    if not isinstance(extensions, Mapping):
        return diagnostics
    for namespace, extension in extensions.items():
        if namespace in _SUPPORTED_EXTENSIONS or not isinstance(extension, Mapping):
            continue
        if extension.get("required") is True:
            diagnostics.append(
                _diag(
                    "HDP-SEM-UNSUPPORTED-REQUIRED-EXTENSION",
                    f"required extension {namespace!r} is not supported by this consumer",
                    f"/extensions/{namespace}",
                    "SEM-080",
                )
            )
    return diagnostics


def _check_stage_graph(document: Mapping[str, Any]) -> List[Diagnostic]:
    stages = document.get("orchestration", {}).get("stages", [])
    if not stages:
        return []
    identifiers = [str(item.get("id")) for item in stages]
    adjacency = {
        str(item.get("id")): [str(target) for target in item.get("next", [])]
        for item in stages
    }
    diagnostics: List[Diagnostic] = []
    reached: Set[str] = set()
    frontier = [identifiers[0]]
    while frontier:
        current = frontier.pop()
        if current in reached:
            continue
        reached.add(current)
        frontier.extend(adjacency.get(current, []))
    for index, identifier in enumerate(identifiers):
        if identifier not in reached:
            diagnostics.append(
                _diag(
                    "HDP-SEM-UNREACHABLE-STAGE",
                    f"stage {identifier!r} is unreachable from the first declared stage",
                    f"/orchestration/stages/{index}",
                    "SEM-053",
                )
            )

    visiting: Set[str] = set()
    visited: Set[str] = set()
    cycle_nodes: Set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            cycle_nodes.add(identifier)
            return
        if identifier in visited:
            return
        visiting.add(identifier)
        for target in adjacency.get(identifier, []):
            visit(target)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in identifiers:
        visit(identifier)
    if cycle_nodes:
        diagnostics.append(
            _diag(
                "HDP-SEM-UNBOUNDED-STAGE-CYCLE",
                "workflow cycles require an explicit bounded-loop construct; v0.1 stages are acyclic",
                "/orchestration/stages",
                "SEM-054",
                *sorted(cycle_nodes),
            )
        )
    return diagnostics


def _check_traceability(document: Mapping[str, Any]) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []
    nodes = document.get("traceability", {}).get("nodes", [])
    edges = document.get("traceability", {}).get("edges", [])
    node_ids = _ids(nodes)
    node_by_id = {
        str(item.get("id")): item
        for item in nodes
        if isinstance(item, Mapping) and item.get("id") is not None
    }

    controls = set().union(
        _ids(_records(document, ("safety", "securityControls"))),
        _ids(_records(document, ("safety", "privacyControls"))),
        _ids(_records(document, ("safety", "safetyConstraints"))),
    )
    artifacts = _ids(_records(document, ("contracts", "artifacts")))
    entity_ids = {
        "outcome": _ids(_records(document, ("purpose", "intendedOutcomes"))),
        "requirement": _ids(_records(document, ("requirements",))),
        "component": artifacts,
        "test": _ids(_records(document, ("evaluation", "tests"))),
        "evidence": artifacts,
        "risk": _ids(_records(document, ("risks",))),
        "control": controls,
        "decision": _ids(_records(document, ("success", "acceptanceCriteria"))),
    }
    for index, node in enumerate(nodes):
        kind = node.get("kind")
        reference = node.get("ref")
        if reference not in entity_ids.get(str(kind), set()):
            diagnostics.append(
                _diag(
                    "HDP-SEM-TRACE-REF-MISSING",
                    f"{kind} trace node references unknown {kind} entity {reference!r}",
                    f"/traceability/nodes/{index}/ref",
                    "SEM-061",
                )
            )

    edge_indexes: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    for index, edge in enumerate(edges):
        for field in ("from", "to"):
            if edge.get(field) not in node_ids:
                diagnostics.append(
                    _diag(
                        "HDP-SEM-TRACE-NODE-MISSING",
                        f"trace edge {field} references unknown node {edge.get(field)!r}",
                        f"/traceability/edges/{index}/{field}",
                        "SEM-060",
                    )
                )
        source = node_by_id.get(str(edge.get("from")))
        target = node_by_id.get(str(edge.get("to")))
        if source is None or target is None:
            continue
        relation = str(edge.get("relation"))
        edge_indexes.setdefault((str(edge.get("from")), relation), []).append(
            (index, str(edge.get("to")))
        )
        endpoint_kinds = (str(source.get("kind")), str(target.get("kind")))
        allowed_endpoints = {
            "decomposedInto": {("outcome", "requirement")},
            "implementedBy": {("requirement", "component")},
            "verifiedBy": {
                ("requirement", "test"), ("component", "test"),
                ("control", "test"),
            },
            "validatedBy": {("outcome", "test")},
            "produces": {("test", "evidence")},
            "mitigates": {("control", "risk")},
            "supports": {("evidence", "decision")},
            "refutes": {("evidence", "decision")},
        }
        if relation == "supersedes":
            valid_endpoints = endpoint_kinds[0] == endpoint_kinds[1]
        else:
            valid_endpoints = endpoint_kinds in allowed_endpoints.get(relation, set())
        if not valid_endpoints:
            diagnostics.append(
                _diag(
                    "HDP-SEM-TRACE-EDGE-TYPE",
                    f"{relation} cannot connect {endpoint_kinds[0]} to {endpoint_kinds[1]}",
                    f"/traceability/edges/{index}",
                    "SEM-062",
                )
            )

    tests_by_id = {
        str(item.get("id")): item
        for item in _records(document, ("evaluation", "tests"))
    }
    requirement_by_id = {
        str(item.get("id")): item
        for item in _records(document, ("requirements",))
    }

    def requirement_has_path(requirement_node_id: str) -> bool:
        requirement_node = node_by_id.get(requirement_node_id, {})
        requirement_id = str(requirement_node.get("ref"))
        requirement = requirement_by_id.get(requirement_id, {})
        verification_ids = set(requirement.get("verificationIds", []))
        for _, component_id in edge_indexes.get(
            (requirement_node_id, "implementedBy"), []
        ):
            component = node_by_id.get(component_id, {})
            if component.get("kind") != "component":
                continue
            for _, test_node_id in edge_indexes.get((component_id, "verifiedBy"), []):
                test_node = node_by_id.get(test_node_id, {})
                test_id = str(test_node.get("ref"))
                test = tests_by_id.get(test_id, {})
                if (
                    test_node.get("kind") != "test"
                    or test_id not in verification_ids
                    or requirement_id not in test.get("requirementIds", [])
                ):
                    continue
                for _, evidence_id in edge_indexes.get((test_node_id, "produces"), []):
                    evidence = node_by_id.get(evidence_id, {})
                    if (
                        evidence.get("kind") == "evidence"
                        and evidence.get("ref") == test.get("evidenceArtifactId")
                    ):
                        return True
        return False

    nodes_by_kind_and_ref: Dict[Tuple[str, str], List[str]] = {}
    for node_id, node in node_by_id.items():
        nodes_by_kind_and_ref.setdefault(
            (str(node.get("kind")), str(node.get("ref"))), []
        ).append(node_id)

    outcomes = _records(document, ("purpose", "intendedOutcomes"))
    for index, outcome in enumerate(outcomes):
        outcome_id = str(outcome.get("id"))
        covered = False
        for outcome_node_id in nodes_by_kind_and_ref.get(("outcome", outcome_id), []):
            for _, requirement_node_id in edge_indexes.get(
                (outcome_node_id, "decomposedInto"), []
            ):
                requirement_node = node_by_id.get(requirement_node_id, {})
                if (
                    requirement_node.get("kind") == "requirement"
                    and requirement_has_path(requirement_node_id)
                ):
                    covered = True
                    break
            if covered:
                break
        if not covered:
            diagnostics.append(
                _diag(
                    "HDP-SEM-TRACE-COVERAGE",
                    f"outcome {outcome_id!r} lacks an ordered outcome -> requirement -> component -> test -> evidence path",
                    f"/purpose/intendedOutcomes/{index}/id",
                    "SEM-063",
                )
            )

    for index, requirement in enumerate(_records(document, ("requirements",))):
        if requirement.get("priority") != "must":
            continue
        requirement_id = str(requirement.get("id"))
        trace_nodes = nodes_by_kind_and_ref.get(("requirement", requirement_id), [])
        if not any(requirement_has_path(node_id) for node_id in trace_nodes):
            diagnostics.append(
                _diag(
                    "HDP-SEM-TRACE-COVERAGE",
                    f"MUST requirement {requirement_id!r} lacks an ordered requirement -> component -> declared test -> expected evidence path",
                    f"/requirements/{index}/id",
                    "SEM-064",
                )
            )
    return diagnostics


def semantic_diagnostics(document: Dict[str, Any], base_path: Path) -> List[Diagnostic]:
    """Return deterministic cross-field errors for a structurally valid HDP."""

    del base_path  # Reserved for digest-bound artifact checks in a future version.
    diagnostics: List[Diagnostic] = []
    diagnostics.extend(_check_unique_ids(document))
    diagnostics.extend(_check_refs(document))
    diagnostics.extend(_check_permission_paths(document))
    diagnostics.extend(_check_evaluation(document))
    diagnostics.extend(_check_generation_completeness(document))
    diagnostics.extend(_check_profile_obligations(document))
    diagnostics.extend(_check_extensions(document))
    diagnostics.extend(_check_stage_graph(document))
    diagnostics.extend(_check_traceability(document))
    return sorted(
        diagnostics,
        key=lambda item: (item.instance_path, item.code, item.message),
    )
