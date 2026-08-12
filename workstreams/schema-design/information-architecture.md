# Harness Definition Package: Information Architecture

Status: design draft
Serialization target: JSON Schema Draft 2020-12 with YAML authoring

## 1. Design goals

The package architecture prioritizes:

- modular authoring without losing a deterministic resolved view;
- strict, typed, cross-document references;
- complete coverage of generation, execution, evaluation, and assurance;
- independent evaluation with hidden-fixture isolation;
- profiles that make conformance claims comparable;
- explicit unknowns instead of permissive omission;
- extension points that cannot weaken core semantics; and
- traceability from intent to evidence and operational intervention.

## 2. Proposed package layout

```text
my-harness.hdp/
├── hdp.yaml                         # package manifest and module index
├── purpose.yaml                     # users, stakeholders, purposes, outcomes
├── operations.yaml                  # environments, tasks, scenarios, assumptions
├── requirements.yaml                # normative requirements and exclusions
├── measures.yaml                    # measures, thresholds, decision rules
├── models.yaml                      # model/provider capabilities and constraints
├── contracts.yaml                   # inputs, outputs, artifacts, schemas
├── context.yaml                     # knowledge sources and context assembly
├── tools.yaml                       # tools, interfaces, side effects
├── orchestration.yaml               # roles, control flow, delegation
├── state.yaml                       # state, memory, checkpoints, lifecycle
├── governance.yaml                  # permissions, data rules, approvals
├── resources.yaml                   # cost/token/time/rate budgets and stops
├── resilience.yaml                  # failures, recovery, escalation
├── observability.yaml               # events, traces, evidence capture, interventions
├── safety.yaml                      # safety, security, privacy, compliance
├── evaluation.yaml                  # plans, datasets, scenarios, metrics, evaluators
├── runtime.yaml                     # deployment and runtime constraints
├── monitoring.yaml                  # baselines, drift, alerts, reassessment
├── traceability.yaml                # typed trace graph and assurance claims
├── evolution.yaml                   # compatibility, deprecation, migrations
├── risks.yaml                       # limitations, risks, treatments, acceptance
├── profiles/
│   └── production.yaml              # selected conformance profile overlay
├── schemas/                         # local input/output and artifact schemas
├── fixtures/public/                 # distributable non-secret fixtures only
├── policies/                        # referenced policy bundles or policy metadata
└── extensions/<reverse-dns-owner>/  # isolated vendor/organization extensions
```

This is a logical layout, not a requirement that every package use separate physical files. Small packages MAY inline modules in `hdp.yaml`; the resolved information model is identical.

Hidden fixtures and answer keys are intentionally absent. The public package contains only opaque fixture-set references and expected custody metadata. A separate evaluator package resolves them inside the evaluator trust boundary.

## 3. Manifest responsibilities

`hdp.yaml` is the only mandatory entrypoint. It identifies:

- package identity, HDP version, package version, authorship, license, and provenance;
- declared conformance profiles and capabilities;
- module locations, media types, expected digests, and requirement status;
- imports and resolution constraints;
- extension namespaces;
- canonicalization and digest rules; and
- the requested validation rule set.

The manifest MUST NOT contain implicit path globs. Every normative module is explicitly indexed, preventing unreviewed files from entering a resolution.

## 4. Field-family map

| Required field family | Primary module | Important linked modules |
|---|---|---|
| Identity and provenance | `hdp.yaml` | `traceability.yaml`, `evolution.yaml` |
| Purpose, users, outcomes | `purpose.yaml` | `measures.yaml`, `evaluation.yaml` |
| Operational context and tasks | `operations.yaml` | `runtime.yaml`, `contracts.yaml` |
| Assumptions, dependencies, exclusions | `operations.yaml`, `requirements.yaml` | `risks.yaml`, `traceability.yaml` |
| Measures and thresholds | `measures.yaml` | `purpose.yaml`, `evaluation.yaml`, `monitoring.yaml` |
| Requirements | `requirements.yaml` | all implementation modules, `traceability.yaml` |
| Model/provider constraints | `models.yaml` | `resources.yaml`, `safety.yaml`, `runtime.yaml` |
| Input/output/artifact contracts | `contracts.yaml` | `operations.yaml`, `evaluation.yaml`, `observability.yaml` |
| Context and knowledge | `context.yaml` | `governance.yaml`, `safety.yaml`, `monitoring.yaml` |
| Tools and interfaces | `tools.yaml` | `governance.yaml`, `resilience.yaml`, `observability.yaml` |
| Control, orchestration, roles, delegation | `orchestration.yaml` | `tools.yaml`, `resources.yaml`, `governance.yaml` |
| State, memory, lifecycle | `state.yaml` | `governance.yaml`, `resilience.yaml`, `runtime.yaml` |
| Permissions, data, approvals | `governance.yaml` | `tools.yaml`, `safety.yaml`, `state.yaml` |
| Budgets, time, rates, stops | `resources.yaml` | `orchestration.yaml`, `resilience.yaml`, `monitoring.yaml` |
| Failures, recovery, escalation | `resilience.yaml` | `resources.yaml`, `observability.yaml` |
| Observability, tracing, interventions | `observability.yaml` | `traceability.yaml`, `monitoring.yaml` |
| Safety, security, privacy, compliance | `safety.yaml` | `governance.yaml`, `risks.yaml`, `evaluation.yaml` |
| Evaluation datasets, scenarios, fixtures, metrics, evaluators | `evaluation.yaml` | `measures.yaml`, `contracts.yaml`, `traceability.yaml` |
| Negative, adversarial, regression evaluation | `evaluation.yaml` | `risks.yaml`, `evolution.yaml` |
| Runtime and deployment | `runtime.yaml` | `models.yaml`, `governance.yaml`, `observability.yaml` |
| Monitoring and drift | `monitoring.yaml` | `measures.yaml`, `observability.yaml`, `evolution.yaml` |
| Traceability | `traceability.yaml` | every normative module |
| Change, compatibility, deprecation | `evolution.yaml` | `hdp.yaml`, `monitoring.yaml`, `traceability.yaml` |
| Limitations and risks | `risks.yaml` | `safety.yaml`, `purpose.yaml`, `traceability.yaml` |

## 5. Module envelope

Every module uses a common envelope:

```yaml
kind: HDPRequirements
apiVersion: hdp.dev/v0alpha1
metadata:
  id: urn:hdp:example:case-triage:requirements
  title: Case triage requirements
  version: 0.3.0
  status: draft
  provenance:
    authoredBy:
      - principalRef: urn:principal:example:team-ai
    sourceDigest: sha256:...
spec:
  requirements: []
extensions: {}
```

`kind` selects a module schema. `apiVersion` selects the HDP vocabulary. `metadata.id` is stable across locations; `metadata.version` changes when module content changes. `spec` is kind-specific. `extensions` is the only open namespace in the core model.

## 6. Identity and references

### 6.1 IDs

- Package and top-level entity IDs MUST be globally unique URIs, preferably URNs under an organization-controlled namespace.
- Child entities MAY use package-scoped compact IDs matching `^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$`.
- A canonical typed reference is `{ref: <URI-or-compact-ID>, expectedKind: <kind>}`.
- Labels and file paths MUST NOT be used as identity.
- Renaming an ID is a breaking change unless an explicit migration alias and expiry are declared.

### 6.2 Reference resolution

Resolution order is deterministic:

1. match a fully qualified URI;
2. match an entity in the current module by compact ID;
3. match an imported namespace alias explicitly declared by the manifest;
4. fail as unresolved.

There is no implicit network retrieval during validation. Remote imports MUST be fetched by a separate resolver, constrained by allowlists and digest pins, before validation.

### 6.3 Typed-reference checks

Structural schemas validate reference syntax. Semantic validation verifies that:

- the target exists in the resolved package;
- the target kind is allowed by the referring field;
- the target is enabled by the selected profile;
- the target lifecycle status is usable; and
- the import digest and namespace match the manifest.

## 7. Authoring, normalization, and canonical form

YAML is the human-authoring format; JSON is the schema-validation data model. Before validation, tooling MUST:

1. reject duplicate mapping keys, custom YAML tags, non-string map keys, and merge keys;
2. resolve neither arbitrary objects nor environment-variable interpolation;
3. parse using the YAML 1.2 core schema;
4. convert to JSON-compatible values;
5. apply profile selection and explicitly declared defaults;
6. resolve imports and references without network access;
7. emit canonical JSON using a specification-selected JSON canonicalization method; and
8. calculate the resolution digest over canonical JSON plus referenced artifact digests.

YAML aliases SHOULD be rejected in the baseline profile because alias expansion complicates security review and source-location reporting. Timestamps and durations are strings; decimal quantities that affect budgets or thresholds SHOULD use string decimal representations plus explicit units to avoid binary floating-point ambiguity.

## 8. Composition and overlay rules

The resolved package is formed in this order:

1. load the manifest and pinned imports;
2. load explicitly indexed modules;
3. validate module envelopes and kinds;
4. select exactly one base profile and zero or more compatible capability profiles;
5. apply overlays using typed operations (`add`, `replace`, `remove`, `require`) against stable IDs;
6. reject attempts to weaken protected requirements, controls, or evaluation thresholds;
7. materialize declared defaults; and
8. freeze the resolved graph and digest it.

Raw YAML merge semantics and generic JSON Merge Patch are not used for normative overlays because they cannot express protection or intent safely.

## 9. Validation architecture

Validation produces separate machine-readable reports for these layers:

| Layer | Question | Typical failures |
|---|---|---|
| L0 transport | Can files be safely loaded? | duplicate key, unsupported tag, digest mismatch |
| L1 structural | Does each document satisfy its Draft 2020-12 schema? | wrong type, missing field, unknown core field |
| L2 referential | Do typed references resolve? | missing target, wrong target kind, import mismatch |
| L3 semantic | Are cross-document invariants satisfied? | outcome lacks metric; mutable model lacks snapshot policy |
| L4 profile conformance | Are all obligations for the selected profile met? | missing adversarial suite; insufficient evidence grade |
| L5 implementation verification | Does the harness realize the resolved package? | tool grants differ; stop condition not enforced |
| L6 outcome validation | Does it work for intended users and scenarios? | measure below threshold; unsafe side effect |
| L7 operational assurance | Does evidence support a current scoped claim? | expired evidence; drift trigger; changed subject digest |

Reports preserve `pass`, `fail`, `warning`, `not-run`, `not-applicable`, and `inconclusive` without collapsing them.

## 10. Profiles and conformance classes

Profiles are cumulative obligation sets, not marketing labels:

- **core**: package identity, task/outcome contract, requirements, typed references, budgets, evaluation plan, traceability, and structural/semantic validity.
- **development**: core plus public fixtures, generator derivation, deterministic checks, basic telemetry, and regression suite.
- **controlled**: development plus least-privilege tool grants, data classification, approval gates, evaluator isolation, negative/adversarial evaluation, and evidence retention.
- **production**: controlled plus pinned deployment/runtime, incident escalation, monitoring/drift baselines, rollback, SLOs, change invalidation, and operational-assurance evidence.
- **high-assurance**: production plus independent evaluator operation, stronger artifact attestations, protected evaluation custody, separation of duties, formal risk acceptance, and profile-defined evidence grades.

Capability profiles (for example `interactive-agent`, `batch-decisioning`, `multi-agent`, or `regulated-data`) add domain obligations. A claim names the HDP version, base profile, capability profiles, harness subject digest, validator/evaluator versions, result, date, and evidence manifest.

## 11. Traceability architecture

Traceability is a typed graph rather than fields scattered across modules. Nodes are entity references or evidence subjects. Edges use a controlled vocabulary:

- `operationalizes`: requirement → harness control;
- `verifiedBy`: requirement/control → test or inspection;
- `validatedBy`: outcome → evaluation plan or scenario;
- `measuredBy`: outcome/monitoring objective → measure;
- `mitigates`: control/evaluation → risk;
- `produces`: run/evaluator → artifact/evidence;
- `supports` / `refutes`: evidence → claim;
- `dependsOn`: entity → assumption/dependency;
- `supersedes`: versioned entity → prior entity; and
- `invalidatedBy`: claim → change/drift/incident trigger.

Semantic validation enforces required paths. For example, every mandatory requirement must reach at least one verification method and expected evidence record; every outcome must reach a metric, threshold, evaluation scenario, evaluator, and evidence contract.

## 12. Evaluation custody split

The public HDP includes:

- evaluation plan IDs and versions;
- public scenario definitions and public fixtures;
- opaque hidden dataset/fixture-set IDs, integrity commitments, custodians, allowed evaluator identities, and release policy;
- metrics, scoring/aggregation rules, uncertainty handling, and pass thresholds;
- evaluator interface contracts and expected result schema; and
- leakage tests and attestation requirements.

The evaluator-owned package includes hidden fixture content, answer keys, evaluator prompts, scoring secrets, and blind labels. It is resolved only in an evaluation environment inaccessible to the harness. Results expose the minimum evidence needed for audit without releasing protected material.

## 13. Extensions

Core schemas are closed by default. Extensions appear only under reverse-DNS keys, for example:

```yaml
extensions:
  com.example.hdp.gpu-placement/v1:
    minVramGiB: 48
```

Each extension declares an owning URI, schema URI and digest, version, compatibility range, whether it is required for execution or assurance, and handling for unknown consumers. An extension MUST NOT override core fields, relax a core/profile obligation, create hidden permissions, or alter the meaning of a core result. Required unknown extensions make the package non-conformant for that consumer; optional unknown extensions are preserved and reported.

## 14. Versioning and compatibility

Three versions are distinct:

- **specification version** (`apiVersion`): HDP vocabulary and semantics;
- **package/module version**: author-controlled semantic version;
- **subject revision**: immutable digest or provider revision of a runtime artifact.

Compatibility is declared as `backward`, `forward`, `full`, or `breaking`, with the affected profiles/capabilities and migration reference. Deprecations include announcement, replacement, removal version/date, migration, and assurance impact. A compatibility claim is verified against representative old/new fixtures, not inferred from semantic-version labels alone.

## 15. Information disclosure boundaries

An HDP carries metadata and opaque handles, not secrets. The baseline information classes are:

- `public`;
- `internal`;
- `confidential`;
- `restricted`;
- `evaluation-hidden`.

The harness distribution MUST exclude `evaluation-hidden`. Observability and evidence views MUST apply field-level redaction and audience policies. A trace link can reference protected evidence without revealing its content.
