# Harness Definition Package: Schema Design

Status: design draft; not a final integrated schema
Normative schema dialect: `https://json-schema.org/draft/2020-12/schema`

## 1. Schema package

The proposed schema distribution is independently versioned from any HDP instance:

```text
schema/hdp/v0alpha1/
├── manifest.schema.json
├── common.schema.json
├── module-envelope.schema.json
├── purpose.schema.json
├── operations.schema.json
├── requirements.schema.json
├── measures.schema.json
├── models.schema.json
├── contracts.schema.json
├── context.schema.json
├── tools.schema.json
├── orchestration.schema.json
├── state.schema.json
├── governance.schema.json
├── resources.schema.json
├── resilience.schema.json
├── observability.schema.json
├── safety.schema.json
├── evaluation.schema.json
├── runtime.schema.json
├── monitoring.schema.json
├── traceability.schema.json
├── evolution.schema.json
├── risks.schema.json
├── profile.schema.json
├── validation-report.schema.json
├── derivation-manifest.schema.json
├── execution-record.schema.json
├── evaluation-result.schema.json
└── assurance-claim.schema.json
```

Every schema has an immutable HTTPS `$id`, explicit `$schema`, `title`, and schema-package version annotation. Published schema bytes are content-addressed in the release manifest. Validators MUST use the declared dialect and MUST NOT silently substitute another meta-schema.

## 2. Draft 2020-12 conventions

- Reusable definitions live under `$defs`.
- Core objects use `unevaluatedProperties: false`; extension maps are explicitly open only to registered extension keys.
- Union types use a required discriminator (`kind`, `type`, or `method`) plus `oneOf` branches.
- Conditional requirements use `if`/`then`/`else` only for local structural relations. Cross-document rules belong to semantic validation.
- `$dynamicRef`/`$dynamicAnchor` MAY support profile-defined requirement specializations, but MUST NOT permit an extension to replace a core constraint.
- `format` is annotation-only unless a conformance profile explicitly requires format assertion. Critical formats also have `pattern` or semantic validation.
- Defaults are annotations. Validators MUST NOT mutate instances from a `default` keyword; the resolver materializes specification-defined defaults before digesting.
- Unknown core properties are errors. Unknown registered optional extensions are preserved with warnings; unknown required extensions are errors.

## 3. Common scalar and record types

`common.schema.json` defines the following:

| Type | Shape and constraints |
|---|---|
| `CanonicalUri` | absolute URI string; no relative identity |
| `CompactId` | lowercase stable identifier, 1–128 characters |
| `SemVer` | semantic version without a mutable alias |
| `Digest` | `{algorithm: "sha256", value: <64 lowercase hex>}` |
| `TypedRef` | `{ref, expectedKind}`; optional `packageDigest` for imported targets |
| `PrincipalRef` | typed reference plus declared principal category |
| `Timestamp` | RFC 3339 string with timezone; semantic validator normalizes to UTC |
| `Duration` | ISO 8601 duration string; calendar durations disallowed for runtime limits |
| `Quantity` | `{value: <decimal string>, unit: <controlled unit>}` |
| `Status` | `draft`, `active`, `deprecated`, `retired` |
| `RequirementLevel` | `must`, `should`, `may`, `must-not`, `should-not` |
| `Result` | `pass`, `fail`, `warning`, `not-run`, `not-applicable`, `inconclusive` |
| `Classification` | `public`, `internal`, `confidential`, `restricted`, `evaluation-hidden` |
| `Condition` | versioned expression `{language, languageVersion, expression}` |
| `Owner` | principal reference, responsibility, escalation reference |
| `SourceLocation` | module ID plus JSON Pointer; optionally authoring file/line annotations |
| `UnknownValue` | `{status: unknown, reason, ownerRef, resolveBy, impact}` |
| `Waiver` | scope, justification, approver, issue/expiry, compensating controls |

`Condition.language` is profile-controlled. The baseline permits only `cel` with a fixed HDP environment and no network, file, time, random, reflection, or host calls. Expressions are evaluated against the frozen resolved package or a declared execution record, never arbitrary process state.

## 4. Manifest schema sketch

This sketch illustrates the root shape; it is not the final schema artifact:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.hdp.dev/v0alpha1/manifest.schema.json",
  "type": "object",
  "required": ["kind", "apiVersion", "metadata", "spec"],
  "properties": {
    "kind": {"const": "HarnessDefinitionPackage"},
    "apiVersion": {"const": "hdp.dev/v0alpha1"},
    "metadata": {"$ref": "common.schema.json#/$defs/PackageMetadata"},
    "spec": {
      "type": "object",
      "required": ["schemaDialect", "modules", "profiles", "validation"],
      "properties": {
        "schemaDialect": {"const": "https://json-schema.org/draft/2020-12/schema"},
        "modules": {
          "type": "array",
          "minItems": 1,
          "items": {"$ref": "#/$defs/moduleEntry"}
        },
        "imports": {"type": "array", "items": {"$ref": "#/$defs/import"}},
        "profiles": {"type": "array", "minItems": 1, "items": {"$ref": "common.schema.json#/$defs/TypedRef"}},
        "capabilities": {"type": "array", "items": {"$ref": "common.schema.json#/$defs/CompactId"}},
        "validation": {"$ref": "#/$defs/validationSelection"},
        "canonicalization": {"$ref": "#/$defs/canonicalization"},
        "extensions": {"$ref": "common.schema.json#/$defs/Extensions"}
      },
      "unevaluatedProperties": false
    }
  },
  "unevaluatedProperties": false
}
```

Each module entry includes `kind`, `href`, `mediaType`, `required`, and `digest`. Each import also includes `packageId`, `versionConstraint`, immutable `resolvedVersion`, digest, namespace alias, and provenance. Relative `href` is permitted only within the package root after path traversal and symlink checks.

## 4.1 Integrated top-level projection

Generators that consume a single document use a deterministic **resolved projection**. The following established top-level keys are preserved. They are integration aliases over the modular entities, not a second semantic model:

```yaml
apiVersion: hdp.dev/v0alpha1
kind: HarnessDefinition
metadata:
  id: urn:hdp:example:case-triage
  name: case-triage
  version: 0.3.0
  status: draft
  provenance:
    authors: []
    sourcePackageDigest: sha256:...
    resolvedAt: '2026-08-12T00:00:00Z'
    resolver: {id: urn:tool:hdp-resolver, version: 0.1.0}
purpose:
  statement: Assist authorized case workers with intake triage.
  intendedUsers: []
  intendedOutcomes: []
  nonGoals: []
  prohibitedUses: []
operationalContext:
  environments: []
  tasks: []
  scenarios: []
  assumptions: []
  dependencies: []
  exclusions: []
success:
  measures: []
  thresholds: []
  acceptanceCriteria: []
  serviceObjectives: []
requirements: []
models:
  capabilityNeeds: []
  modelPolicies: []
  providerPolicies: []
  routingPolicies: []
contracts:
  inputs: []
  outputs: []
  artifacts: []
  interfaces: []
context:
  sources: []
  assemblyPolicies: []
  retrievalPolicies: []
  instructionLayers: []
tools:
  definitions: []
  policies: []
  sandboxes: []
orchestration:
  roles: []
  stages: []
  flows: []
  delegations: []
  humanControlPoints: []
state:
  stores: []
  memoryPolicies: []
  checkpoints: []
  lifecycle: []
governance:
  principals: []
  permissions: []
  dataPolicies: []
  approvalPolicies: []
resources:
  budgets: []
  deadlines: []
  rateLimits: []
  stoppingConditions: []
failures:
  modes: []
  recoveryPolicies: []
  retryPolicies: []
  fallbacks: []
  escalations: []
observability:
  events: []
  tracing: []
  evidenceContracts: []
  interventions: []
safety:
  assets: []
  threats: []
  harms: []
  controls: []
  privacyPolicies: []
  complianceObligations: []
evaluation:
  boundary:
    separation: logical
    harnessForbiddenAccess: [hidden-fixtures, answer-keys, evaluator-prompts]
    evaluatorForbiddenAccess: [harness-control, harness-secrets]
  datasets: []
  fixtures: []
  scenarios: []
  tests: []
  metrics: []
  evaluators: []
  negativeSuites: []
  adversarialSuites: []
  regressionSuites: []
runtime:
  profile: production
  targets: []
  deployments: []
  artifacts: []
  environmentBindings: []
monitoring:
  baselines: []
  signals: []
  driftRules: []
  alerts: []
  reassessmentTriggers: []
traceability:
  nodes: []
  edges: []
  verificationMethods: []
  evidenceRecords: []
  claims: []
evolution:
  changes: []
  compatibilityClaims: []
  deprecations: []
  migrations: []
limitations: []
risks:
  register: []
  acceptances: []
  openQuestions: []
extensions: {}
```

Projection mappings are fixed:

| Integrated key | Modular source |
|---|---|
| `metadata` | manifest `metadata` plus resolver provenance |
| `purpose.intendedOutcomes` | `purpose.yaml` `spec.outcomes` |
| `operationalContext.assumptions` | `operations.yaml` `spec.assumptions` |
| `success.acceptanceCriteria` | `measures.yaml` `spec.decisionRules` |
| `requirements` | `requirements.yaml` `spec.requirements` |
| `governance.permissions` | `governance.yaml` `spec.grants` |
| `resources.stoppingConditions` | `resources.yaml` `spec.stopConditions` |
| `failures.recoveryPolicies` | `resilience.yaml` `spec.recoveryProcedures` |
| `evaluation.tests` | `evaluation.yaml` `spec.suites` plus scenario bindings |
| `evaluation.boundary` | evaluator separation and leakage-control projection |
| `evaluation.metrics` | `evaluation.yaml` `spec.metrics` |
| `runtime.profile` | selected base conformance/runtime profile |
| `orchestration.roles` | `orchestration.yaml` `spec.roles` |
| `orchestration.stages` | normalized flow states in execution order |
| `traceability` | `traceability.yaml` complete typed graph |

The resolver MUST record the source module ID and JSON Pointer for every projected array member. Round-trip editing of the projection is not required in v1; modular source remains authoritative.

## 5. Module field design

### 5.1 Purpose: users and outcomes

`purpose.schema.json` contains:

- `purposes[]`: ID, problem statement, intended value, scope, owner, and success horizon;
- `users[]`: ID, user class, needs, capabilities/accessibility attributes, foreseeable vulnerabilities, and excluded uses;
- `stakeholders[]`: interests, responsibilities, decision rights, and potential harms;
- `outcomes[]`: subject/user reference, observable effect, timeframe, measure references, risk references, priority, and acceptance decision reference;
- `nonGoals[]` and `prohibitedUses[]`.

Outcome text cannot substitute for `measureRefs` and a decision rule.

### 5.2 Operations: context, tasks, assumptions, dependencies, exclusions

`operations.schema.json` contains:

- `environments[]`: external systems, actors, data, network/time characteristics, jurisdiction, volatility, and verified/assumed conditions;
- `tasks[]`: input/output contract references, preconditions, completion conditions, allowed side effects, task class, applicable profile, scenario and outcome references;
- `scenarios[]`: task reference, initial state, actors, event sequence, perturbations, expected observations, and applicability;
- `assumptions[]`: statement, basis, validation method, owner, expiry, consequence if false;
- `dependencies[]`: identity/version, criticality, availability/SLO assumption, failure behavior, substitute, license, and provenance;
- `exclusions[]`: excluded condition/use/user/environment and explicit effect on claim scope.

### 5.3 Measures and thresholds

`measures.schema.json` contains:

- `measures[]`: construct, operational definition, unit, direction, population, sampling plan, aggregation, uncertainty method, and data source;
- `thresholds[]`: measure reference, comparator, target, minimum sample size, confidence/credible requirement, segment rules, and hard/soft gate;
- `decisionRules[]`: Boolean composition of threshold references, missing-data policy, tie policy, and result mapping;
- `serviceObjectives[]`: indicator, objective, window, burn/error budget, and intervention reference.

Thresholds use typed decimal quantities. Statistical thresholds declare sample size and uncertainty treatment; a naked percentage is insufficient for assurance profiles.

### 5.4 Requirements

`requirements.schema.json` contains:

- `requirements[]`: ID, normative level, statement, rationale, source, applicable conditions, subject refs, implementation/control refs, verification method refs, expected evidence refs, priority, status, and waiver;
- `requirementGroups[]`: composition (`all`, `any`, `atLeast`), conditions, and profile mapping;
- `exclusions[]`: scoped non-applicability with rationale and approval.

Requirements are atomic and testable. One record cannot join independent obligations with an unstructured “and.” Semantic rules detect missing verification and invalid waivers.

### 5.5 Model and provider constraints

`models.schema.json` contains:

- `capabilityNeeds[]`: modalities, context window, tool calling, structured output, language, safety, latency, and quality minima;
- `modelPolicies[]`: allow/deny rules, immutable revision preference, fallback compatibility, model-risk tier, and evaluation prerequisites;
- `providerPolicies[]`: allowed providers/regions/endpoints, retention/training constraints, account/tenant, encryption, availability, rate limits, and incident obligations;
- `routingPolicies[]`: selection criteria, fallback order, downgrade prohibition, experiment allocation, and audit fields;
- `samplingPolicies[]`: parameter bounds, repeat/seed strategy where supported, and nondeterminism disclosure.

Credentials are secret references. Model/provider policy permits capability-based portability without pretending model versions are interchangeable.

### 5.6 Input, output, and artifact contracts

`contracts.schema.json` contains:

- `dataContracts[]`: direction, media type, schema URI/digest, size limits, classification, normalization, validation, and compatibility policy;
- `artifactContracts[]`: producer, consumer, format, naming, integrity, custody, retention, required metadata, and acceptance checks;
- `sideEffectContracts[]`: target resource, allowed mutation, authorization, idempotency, confirmation, compensation, and evidence;
- `errorContracts[]`: stable error codes, safe message, retryability, and machine-readable details;
- `interfaceContracts[]`: operations, protocols, timeouts, authentication reference, and version policy.

Schemas for task I/O are pinned by digest. Free-form output is allowed only when the task contract and evaluator explicitly support it.

### 5.7 Context and knowledge

`context.schema.json` contains:

- `sources[]`: identity, origin, authority, license, classification, freshness, integrity, trust, and retrieval interface;
- `contextPolicies[]`: selection, ordering, token allocation, deduplication, citation, conflict resolution, and truncation behavior;
- `retrievalPolicies[]`: query limits, filters, ranking, tenant boundaries, poisoning checks, and cache policy;
- `instructionLayers[]`: authority order, mutability, injection resistance, provenance, and maximum scope;
- `knowledgeSnapshots[]`: source versions/digests, creation time, coverage, known gaps, and expiry.

Hidden evaluation sources MUST NOT appear in any harness-readable source, snapshot, cache, or retrieval index.

### 5.8 Tools, interfaces, and side effects

`tools.schema.json` contains:

- `tools[]`: interface contract, adapter identity/digest, capabilities, side-effect class, data access, authentication handle, network scope, availability, timeout, concurrency, and result contract;
- `toolPolicies[]`: allowed roles/tasks, argument constraints, preconditions, approvals, rate/budget refs, output sanitation, and error policy;
- `sandboxPolicies[]`: filesystem/process/network/device boundaries and isolation strength;
- `humanInterfaces[]`: presentation/confirmation contract, accessibility requirements, and interruption behavior.

Tool declarations describe possible capability; grants in governance describe authorized capability. A tool is unavailable unless both exist.

### 5.9 Control, orchestration, roles, delegation

`orchestration.schema.json` contains:

- `roles[]`: responsibilities, authority, model policy, tool grants, context policy, output contract, and accountability owner;
- `flows[]`: typed states/transitions, entry/exit, conditions, retry/timeout, stop refs, and emitted events;
- `delegations[]`: delegator/delegate role, allowed task classes, depth/fan-out/concurrency bounds, budget transfer, permission non-escalation, context minimization, result validation, cancellation, and accountability;
- `consensusPolicies[]`: quorum, disagreement handling, independence requirements, and tie/escalation;
- `humanControlPoints[]`: notification, review, approval, override, abort, and resume contracts.

Loops and recursion are invalid without explicit bounds. Delegates cannot acquire permissions or budgets their delegator does not possess.

### 5.10 State, memory, and lifecycle

`state.schema.json` contains:

- `stateStores[]`: schema, authority, classification, tenant boundary, consistency, durability, encryption, and access policy;
- `memoryPolicies[]`: scope (`turn`, `run`, `user`, `organization`, `global`), write/read criteria, provenance, correction, expiry, retention, deletion, and opt-out;
- `checkpointPolicies[]`: trigger, atomicity, resume contract, version/digest, and invalidation;
- `lifecycleStates[]`: creation, activation, suspension, completion, archival, deletion, and legal hold transitions;
- `stateMigrations[]`: source/target schema, transformation identity, backup, validation, and rollback.

Model context is not authoritative state unless a contract explicitly makes it so.

### 5.11 Permissions, data, and approvals

`governance.schema.json` contains:

- `principals[]`, `roles[]`, `resources[]`, and `grants[]` with action, scope, condition, purpose, and expiry;
- `dataClasses[]`: sensitivity, residency, retention, allowed uses, disclosure, minimization, and deletion;
- `approvalPolicies[]`: trigger, eligible approvers, quorum, separation of duties, expiry, evidence, and fail-closed behavior;
- `secretRefs[]`: opaque store/key identity, intended consumers, rotation metadata, never the value;
- `consentAndLegalBases[]`: purpose, data subjects, jurisdiction, collection/withdrawal, and record reference.

Policy evaluation is deny-by-default. “Available to runtime” does not imply “granted to harness.”

### 5.12 Budgets, time, rates, and stop conditions

`resources.schema.json` contains:

- `budgets[]`: resource (`tokens`, `cost`, `wallTime`, `cpu`, `memory`, `storage`, `network`, `toolCalls`, custom), hard/soft limit, scope, allocation, and exhaustion behavior;
- `deadlines[]`: source clock, duration/instant, grace, cancellation, and late-result handling;
- `rateLimits[]`: subject, action, window, capacity, burst, queue, and backoff;
- `stopConditions[]`: condition, priority, propagation, required cleanup, evidence, and restart authorization;
- `quotas[]`: period, reset semantics, inheritance, and reservation.

Every execution and delegation tree is covered by at least one hard wall-time and cost/tool-call bound.

### 5.13 Failures, recovery, escalation

`resilience.schema.json` contains:

- `failureModes[]`: trigger, detectability, effect, severity, affected contract, and classification;
- `retryPolicies[]`: eligible failures, max attempts, backoff/jitter, idempotency requirement, deadline interaction, and retry budget;
- `recoveryProcedures[]`: safe state, compensation, checkpoint, data integrity checks, operator action, and outcome;
- `fallbacks[]`: activation condition, substitute, capability loss, user disclosure, and re-evaluation requirement;
- `escalations[]`: trigger, recipient/on-call role, channel abstraction, severity, required payload, acknowledgement, and timeout;
- `continuityPlans[]`: degraded mode, RTO/RPO, restore verification, and drill reference.

### 5.14 Observability, tracing, evidence, interventions

`observability.schema.json` contains:

- `eventTypes[]`: schema, producer, purpose, classification, sampling, and retention;
- `tracePolicies[]`: correlation IDs, parent/child propagation, task/model/tool/evaluator spans, clocks, and redaction;
- `evidenceContracts[]`: subject, collector, artifact contract, integrity, custody, audience, minimum grade, and retention;
- `signals[]`: source, measure, aggregation, threshold reference, dimensions, and cardinality bound;
- `interventions[]`: trigger, actor, allowed action, precondition, approval, rollback, evidence, and post-check;
- `auditPolicies[]`: immutable event requirements, access, export, and verification.

Telemetry MUST exclude raw secrets and hidden fixtures. Redaction happens before export, not only in downstream viewers.

### 5.15 Safety, security, privacy, compliance

`safety.schema.json` contains:

- `assets[]`, `threatActors[]`, `trustBoundaries[]`, `threats[]`, and `controls[]`;
- `harmScenarios[]`: affected party, pathway, severity/likelihood, prevention, detection, response, and measure;
- `securityPolicies[]`: authentication, authorization, isolation, supply chain, vulnerability, secure update, and incident controls;
- `privacyPolicies[]`: purpose limitation, minimization, retention, rights, privacy threat, and privacy evaluation;
- `complianceObligations[]`: source/version/jurisdiction, applicability rationale, control and evidence references, owner, review date, and limitation;
- `contentPolicies[]`: prohibited/controlled behavior, boundary conditions, refusal/escalation, and evaluation references.

An HDP records applicability and control evidence; it does not self-certify legal compliance.

### 5.16 Evaluation, including negative/adversarial/regression

`evaluation.schema.json` contains:

- `evaluationPlans[]`: subject scope, purpose, independence level, dataset/scenario/metric/evaluator refs, execution design, decision rule, and result schema;
- `datasets[]`: opaque/public identity, version/digest commitment, source, sampling frame, segments, rights, classification, contamination policy, and custody;
- `fixtureSets[]`: visibility (`public`, `restricted`, `hidden`), opaque ID, commitment, custodian, access policy, rotation, and disclosure response;
- `evaluationScenarios[]`: task/environment refs, setup, perturbations, expected observations, and blinded labels;
- `metrics[]`: implementation/version, inputs, computation, direction, uncertainty, limitations, and calibration;
- `evaluators[]`: method (`deterministic`, `human`, `model-judge`, `hybrid`), operator, implementation digest, permissions, independence, calibration, conflicts, and fallback;
- `suites[]`: type (`positive`, `negative`, `adversarial`, `regression`, `safety`, `privacy`, `performance`, `recovery`), coverage model, cases, and thresholds;
- `leakageControls[]`: fixture segregation, retrieval exclusion, access monitoring, canary cases, contamination checks, and response;
- `resultPolicies[]`: aggregation, segment floors, flaky/inconclusive handling, repeat policy, adjudication, and publication.

Model-judge scores cannot be treated as ground truth without calibration, uncertainty, bias/segment analysis, and a dispute/adjudication path. Safety-critical hard gates SHOULD use deterministic or human-confirmed evaluation when feasible.

### 5.17 Runtime and deployment

`runtime.schema.json` contains:

- `runtimeTargets[]`: OS/architecture, process/container/VM, dependencies, network, storage, clock, locale, and accelerator;
- `deployments[]`: topology, regions, tenancy, replicas, release strategy, configuration/secret injection, readiness, and rollback;
- `artifacts[]`: identity, digest, SBOM/provenance/attestation refs, source, and signature policy;
- `environmentBindings[]`: HDP environment ref to deployed endpoint/resource binding with verification;
- `healthPolicies[]`: startup/liveness/readiness, dependencies, degraded state, and traffic removal;
- `compatibilityMatrix[]`: runtime/model/tool/adapter versions and tested status.

### 5.18 Monitoring and drift

`monitoring.schema.json` contains:

- `baselines[]`: measure, population/segment, window, sample requirements, value distribution, and subject digest;
- `driftRules[]`: signal, comparator/test, threshold, persistence window, severity, and confounders;
- `monitoringPlans[]`: schedule, coverage, sampling, privacy controls, owner, dashboard/evidence refs;
- `alerts[]`: routing, deduplication, acknowledgement, escalation, and suppression governance;
- `reassessmentTriggers[]`: model/provider/data/context/tool/runtime/policy/incident changes and required evaluation scope;
- `interventionPolicies[]`: warn, throttle, disable capability, rollback, suspend, or require approval;
- `postDeploymentEvaluations[]`: delayed outcomes, user impact, shadow/canary, and decision rules.

Drift is always relative to a pinned baseline and named subject. A threshold without a response is only an observation.

### 5.19 Traceability and claims

`traceability.schema.json` contains:

- `nodes[]`: typed reference or evidence subject;
- `edges[]`: controlled relation, source/target, rationale, applicability, provenance;
- `verificationMethods[]`: method, implementation, environment, expected result/evidence;
- `evidenceRecords[]`: immutable identity, subject, producer/collector, time, digest/signature, custody, classification, and location reference;
- `claims[]`: type, subject digest tuple, scope/profile, rule, result, supporting/refuting evidence, issuer/reviewer, issue/expiry, invalidation triggers, limitations;
- `coveragePolicies[]`: required trace paths and orphan handling.

### 5.20 Change, compatibility, deprecation

`evolution.schema.json` contains:

- `changes[]`: previous/new subject, category, rationale, affected entities, compatibility, risk and assurance impact;
- `compatibilityClaims[]`: direction, profiles/capabilities, test matrix, evidence, limitation;
- `deprecations[]`: target, replacement, announce/remove versions/dates, migration, telemetry, and communication;
- `migrations[]`: preconditions, transformations, verification, rollback, data-loss declaration;
- `invalidationPolicies[]`: changes that expire evaluation/assurance evidence;
- `releasePolicies[]`: approvals, gates, artifacts, rollout, rollback, and evidence.

### 5.21 Limitations and risks

`risks.schema.json` contains:

- `limitations[]`: affected scope/user/outcome, reason, impact, workaround, disclosure location, review trigger;
- `risks[]`: asset/outcome, cause/event/consequence, likelihood, impact, uncertainty, inherent/residual rating, treatment and measure refs;
- `riskAcceptances[]`: residual risk, decision owner/approver, rationale, scope, issue/expiry, review/withdrawal;
- `openQuestions[]`: question, impact, owner, decision date, evidence needed, blocking status;
- `incidents[]` references for assurance invalidation, not full incident contents.

## 6. Human-friendly YAML example

```yaml
kind: HDPEvaluation
apiVersion: hdp.dev/v0alpha1
metadata:
  id: urn:hdp:example:case-triage:evaluation
  title: Independent case-triage evaluation
  version: 0.3.0
  status: draft
  provenance:
    authoredBy:
      - principalRef: urn:principal:example:assurance-team
spec:
  evaluators:
    - id: deterministic-disposition-checker
      method: deterministic
      implementation:
        uri: oci://registry.example/evaluators/disposition-checker@sha256:0123...
      independence:
        boundary: separate-runtime
        operatorRef: urn:principal:example:assurance-team
      permissions:
        - read:evaluation-ingress
      forbiddenAccess:
        - harness-runtime
        - harness-retrieval-index
  fixtureSets:
    - id: blind-regression-v7
      visibility: hidden
      commitment:
        algorithm: sha256
        value: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
      custodianRef: urn:principal:example:assurance-team
      accessPolicyRef:
        ref: hidden-fixture-custody
        expectedKind: ApprovalPolicy
  suites:
    - id: regression-suite
      type: regression
      fixtureSetRefs:
        - ref: blind-regression-v7
          expectedKind: FixtureSet
      metricRefs:
        - ref: disposition-accuracy
          expectedKind: Metric
      decisionRuleRef:
        ref: release-gate
        expectedKind: DecisionRule
extensions: {}
```

## 7. Semantic validation interface

Schema validation cannot enforce graph invariants, independence, or evidence sufficiency. A semantic validator consumes:

```json
{
  "resolvedPackage": "<canonical package graph>",
  "profile": "production",
  "ruleSet": "hdp-semantic/v0alpha1",
  "validator": {"id": "...", "version": "...", "digest": "..."}
}
```

It returns a `validation-report` containing the exact subject digest, rule ID/version, result, severity, JSON Pointer locations, message, related entity refs, and evaluator evidence. Rule exceptions require a valid waiver when the profile permits waiver; protected rules cannot be waived.

## 8. Generation and implementation binding

Generators declare:

- supported HDP/API and profile ranges;
- supported module kinds, condition language, and extensions;
- target runtime and adapter capabilities;
- mappings from HDP entities to generated artifacts;
- unsupported or manual bindings;
- defaults and conflict rules; and
- verification procedures.

The derivation manifest maps every generated artifact and implemented control back to source entities and records all unresolved/manual choices. A generator MUST fail closed when a mandatory concept has no safe target mapping; emitting a TODO while claiming success is non-conformant.

## 9. Evaluator isolation and anti-leakage controls

The formal schemas enforce declared separation; runtime/evidence checks establish actual separation:

1. The evaluator identity cannot be referenced as a harness role or tool.
2. Hidden fixture content cannot appear in package modules, public fixture paths, context sources, retrieval indexes, model fine-tuning inputs, generated artifacts, or harness-readable telemetry.
3. The hidden fixture commitment is recorded before the evaluated run.
4. Evaluator ingress accepts only contracted outputs/observations; no arbitrary harness callbacks.
5. Harness egress to evaluator internals is denied.
6. Evaluator result release is one-way and may be delayed until run closure.
7. Access logs and canary fixtures support leakage detection.
8. Suspected leakage invalidates the affected result and triggers fixture rotation and incident review.

## 10. Conformance result

A conformance result is valid only when it includes:

- HDP spec and rule-set versions;
- base and capability profiles;
- resolved package digest and harness subject tuple;
- validator/generator/evaluator identities and digests;
- all rule results, including non-pass states;
- profile-required evidence with freshness;
- approved waivers and their expiry;
- unsupported extensions or capabilities;
- issue and expiry time plus invalidation triggers; and
- signature or equivalent integrity evidence.

Conformance does not establish fitness. Fitness and operational-assurance claims reference but remain distinct from conformance results.

## 11. Open schema questions

1. Which URI authority will own permanent `$id` values and namespaces?
2. Should the first implementation support a CEL subset or begin with non-executable semantic rules plus validator-specific bindings?
3. Which canonical JSON method and signature envelope are mandatory?
4. Which profile obligations are non-waivable, and which authority governs profile evolution?
5. Are module overlays required in v1, or should v1 prefer explicit resolved packages and defer authored overlays?
6. What minimum independent-evaluator boundary is acceptable for local development versus production assurance?
7. Which controlled vocabularies require registries versus package-local definitions?
8. What privacy-preserving evidence format can support audits without disclosing user data or hidden fixtures?
