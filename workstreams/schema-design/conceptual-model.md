# Harness Definition Package: Conceptual Model

Status: design draft
Intended audience: HDP authors, schema implementers, harness generators, validators, evaluators, and assurance reviewers

## 1. Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** describe proposed normative behavior for a future HDP specification. Because this document is a design draft, they do not yet establish a published standard.

## 2. Core definitions

### 2.1 AI harness

An **AI harness** is the governed executable system around one or more models that turns a task invocation into controlled actions and artifacts. It includes the resolved instructions, context assembly, model and provider adapters, tool interfaces, orchestration and delegation logic, state handling, authorization gates, resource limits, error handling, telemetry, and artifact capture needed to operate the model. A model alone is not a harness; a prompt alone is not a harness.

A harness may be generated from an HDP, configured by an HDP, or assessed against an HDP. The HDP never implies that a generator can fully synthesize every implementation detail.

### 2.2 Harness Definition Package (HDP)

A **Harness Definition Package** is a versioned, declarative, content-addressable collection of linked definitions that specifies:

- the intended users, purposes, outcomes, and operating conditions;
- the requirements and constraints governing a harness;
- the contracts needed to generate, configure, execute, and observe it;
- the independent evaluation plan used to judge outcomes; and
- the traceability and evidence needed to support conformance and assurance claims.

An HDP is a specification artifact, not executable code, a model, a deployment, an evaluation result, or proof that a system is fit for use. An HDP instance MAY include non-secret public fixtures and evidence manifests, but MUST NOT contain production secrets or hidden evaluation answers.

### 2.3 Harness instance

A **harness instance** is a particular resolved and deployed realization of a harness definition. It is identified by the immutable digests of the HDP resolution, implementation, model/provider configuration, runtime, tools, policies, and relevant context snapshot.

### 2.4 Task

A **task** is an adjudicable unit of work with declared inputs, preconditions, expected artifacts or state transitions, applicable constraints, and outcome criteria. A task can contain multiple scenarios. A natural-language aspiration without observable acceptance conditions is not by itself a task contract.

### 2.5 Operating environment

The **operating environment** is everything the harness can observe or affect but does not own: users, organizations, services, data sources, networks, devices, policies, jurisdictions, clocks, and external state. Environment definitions distinguish assumed conditions from conditions that are actively verified.

### 2.6 Runtime

The **runtime** is the computational substrate that loads and executes the harness: process/container/VM boundaries, operating system, libraries, networking, scheduling, secret injection, storage, and deployment topology. The runtime enforces some constraints but does not decide whether task outcomes are acceptable.

### 2.7 Model and provider

A **model** is an inference component with declared capabilities and behavioral limitations. A **provider** supplies access to a model through an interface with provider-specific identity, region, retention, rate, safety, and version semantics. Provider labels such as `latest` are mutable aliases and cannot alone support reproducibility.

### 2.8 Evaluator

An **evaluator** is a component or process that judges evidence from an execution against declared measures. It MUST be logically separate from the harness under evaluation. For assurance-bearing evaluations, it SHOULD also be independently versioned, permissioned, and operated.

An evaluator MAY be deterministic code, a human review protocol, a statistical procedure, a model-based judge, or a declared composition of these. It is not a normal harness tool. Hidden fixtures, answer keys, evaluator prompts, and scoring secrets MUST be inaccessible to the harness and to harness-controlled context retrieval.

### 2.9 Evidence

**Evidence** is a captured observation, artifact, attestation, or evaluator result that can support or refute a claim. Evidence has provenance, collection time, subject identity, integrity metadata, retention policy, and access classification. Logs become evidence only when the applicable evidence contract is satisfied.

## 3. System boundaries

| Element | Owns | Must not be conflated with |
|---|---|---|
| Task | Inputs, preconditions, expected outcome, task-specific criteria | Prompt wording or one implementation path |
| Environment | External conditions and reachable state | Runtime configuration or harness state |
| Model | Inference behavior for supplied input | Orchestration, tools, policy, or provider guarantees |
| Provider | Model access and provider controls | Model behavior in all providers or a stable model version |
| Harness | Context, control flow, tools, state, policy gates, artifact production | Independent outcome judgment |
| Runtime | Execution and enforcement substrate | Business outcome or evaluator |
| Evaluator | Independent scoring or adjudication | A harness self-report or hidden tool available to the harness |
| Evidence store | Integrity-preserving observations and result records | Unstructured logs with unknown provenance |
| HDP | Declarative definition and assurance intent | Generated harness, deployment, run, or assurance certificate |

The evaluator trust boundary is mandatory: the harness can emit declared observations to an evaluation ingress, but cannot query evaluator internals, hidden fixtures, answer keys, future cases, or final labels during the evaluated run.

## 4. Assurance vocabulary

### Generation

**Generation** transforms an HDP, profile, and target adapter into harness source, configuration, deployment descriptors, or test scaffolding. Generation establishes derivation, not correctness. Generator output MUST record source HDP digests, generator identity/version, selected profile, defaults, unresolved choices, and emitted artifact digests.

### Verification

**Verification** is evidence-based checking that an artifact, configuration, implementation, or control satisfies its specified requirements and contracts. It asks whether the subject was defined or built correctly. Verification can be structural, semantic, static, or behavioral, but its scope and subject MUST be named.

### Validation

**Validation** is evidence-based checking that a subject is suitable for its stated users, purpose, outcomes, and operating conditions. It asks whether the right system was defined or built. Validation requires representative scenarios and outcome measures; internal consistency or test coverage alone is not validation.

### Structural validation

**Structural validation** checks a serialized document against its declared JSON Schema vocabulary and schema version. It answers: “Is the document shaped and typed as required?” It does not resolve cross-document meaning.

The phrase “structural validation” follows established schema-tool terminology; at the system-assurance level it is a verification activity and must not be confused with outcome validation.

### Semantic verification

**Semantic verification** determines whether references resolve and whether the package obeys cross-document invariants, policy relations, and internal consistency rules. It answers: “Does this package say something coherent and implementable under the selected profile?”

### Implementation verification

**Implementation verification** determines whether a harness instance implements the resolved HDP requirements and contracts. It answers: “Was the specified harness built/configured correctly?” Static inspection alone is insufficient when behavior is runtime-dependent.

### Outcome validation

**Outcome validation** determines, using declared evaluation methods and representative conditions, whether the harness achieves intended outcomes for intended users. It answers: “Does the realized harness solve the stated problem within its constraints?”

### Conformance

**Conformance** is satisfaction of all mandatory structural, semantic, and implementation obligations for a named HDP specification version, profile, and declared capability set. A conformance claim is always scoped; “HDP-conformant” without version, profile, subject, and evidence is invalid.

### Fitness

**Fitness** is the degree to which a specific harness instance is suitable for a named purpose and operating context, considering outcomes, risks, limitations, and residual uncertainty. Conformance is necessary only when the selected governance says so and is never sufficient proof of fitness.

### Outcome

An **outcome** is an externally meaningful effect experienced by a user, system, or environment. Output production is not necessarily an outcome. Each outcome MUST have at least one observable measure and a decision rule.

### Operational assurance

**Operational assurance** is a time-bounded, evidence-backed claim that a particular harness instance continues to conform and remain acceptably fit under a declared operating envelope. It combines provenance, verification, outcome evaluation, runtime controls, monitoring, drift checks, and incident/change history. It expires or is invalidated when declared change triggers occur.

## 5. Entity model

The conceptual entities and principal relations are:

```text
HDP Package
  defines -> Purpose -> Outcome -> Measure -> Threshold
  defines -> User / Stakeholder
  defines -> Task -> Scenario -> Input/Artifact Contract
  assumes -> Environment / Dependency / Assumption
  excludes -> Exclusion / Unsupported Condition
  constrains -> Requirement / Policy / Budget / Runtime / Model / Provider
  configures -> Harness -> Role / Tool / State / Control Flow
  protects -> Data Class / Asset / Principal
  declares -> Failure Mode -> Recovery / Escalation / Stop Condition
  declares -> Observation -> Evidence Contract
  declares -> Evaluation Plan -> Dataset / Fixture / Metric / Evaluator
  monitors -> Signal / Baseline / Drift Rule / Intervention
  traces -> Claim / Requirement / Test / Evaluation / Evidence / Risk
  evolves through -> Change / Compatibility / Deprecation

Harness Instance
  is realization of -> Resolved HDP
  runs in -> Runtime and Environment
  invokes -> Model / Provider / Tool
  produces -> Artifact / State Transition / Observation

Evaluator
  consumes -> Allowed Observation / Artifact / Hidden Fixture
  produces -> Evaluation Result / Evidence
  supports or refutes -> Claim
```

Every normative entity has a stable typed identifier. Relationships are represented as typed references rather than free-text names. Human labels MAY change without breaking identity.

## 6. Lifecycle and gates

1. **Author**: create modules, requirements, risks, evaluation intent, and trace links.
2. **Resolve**: select profile and target; expand imports; pin defaults; calculate a resolution digest.
3. **Generate/configure**: emit harness artifacts and a derivation manifest.
4. **Validate structure**: run Draft 2020-12 schema checks on every module.
5. **Verify semantics**: resolve typed references and evaluate semantic rules.
6. **Verify implementation**: inspect and exercise the generated/configured harness against contracts.
7. **Execute**: run identified tasks/scenarios within the declared environment, permissions, and budgets.
8. **Evaluate independently**: score permitted outputs and evidence while protecting hidden fixtures.
9. **Issue scoped claims**: record conformance, fitness, and/or operational-assurance claims with evidence and expiry.
10. **Monitor and reassess**: compare signals to baselines; invalidate claims on material drift, incident, or change trigger.

No gate may silently convert `unknown`, `not-run`, `not-applicable`, or `inconclusive` into `pass`.

## 7. Identity, provenance, and snapshots

A reproducible subject is the tuple:

```text
(resolved-hdp-digest,
 implementation-digest,
 generator-id+version,
 model-id+revision,
 provider-config-digest,
 runtime-digest,
 tool-adapter-digests,
 policy-bundle-digest,
 context-snapshot-digests,
 evaluation-plan-digest)
```

Where an element cannot be pinned, the package MUST identify it as mutable, record the resolution time and observed provider metadata, and downgrade reproducibility accordingly.

## 8. Claims and evidence

A claim has:

- a stable claim ID and type (`conformance`, `fitness`, `outcome`, `control-effectiveness`, `operational-assurance`);
- a precise subject and scope;
- a decision rule and applicable requirement/outcome/risk references;
- evidence references with integrity and provenance;
- issuer and independent reviewer where required;
- result (`pass`, `fail`, `inconclusive`, `not-run`, `not-applicable`);
- issue time, expiry, and invalidation triggers; and
- known limitations and residual risks.

Evidence strength is explicit: `assertion`, `inspection`, `test`, `evaluation`, `runtime-observation`, or `independent-attestation`. Profiles can require minimum evidence grades.

## 9. Unknowns and absence

Missing information is never inferred as safe. Required decisions use one of:

- a resolved value;
- an explicit `unknown` with owner and due date;
- a bounded assumption with validation method and expiry;
- an accepted risk with approver and review date; or
- an explicit exclusion that limits the claim scope.

This prevents permissive defaults from becoming accidental requirements or assurance claims.

## 10. Invariants

The following are foundational:

1. The evaluator is outside the harness trust boundary.
2. Hidden evaluation material is not reachable by the harness, model, tools, retrieval indexes, logs exposed during execution, or package distribution.
3. Every intended outcome has a measure and decision threshold.
4. Every normative requirement traces to verification and expected evidence, or is explicitly waived with governance metadata.
5. Every external side effect has an authorization rule and, where risk requires, an approval gate.
6. Every retrying mutation declares idempotency or a compensation strategy.
7. Every loop, delegation chain, and resource consumer is bounded by budgets and stop conditions.
8. Every assurance claim is bound to immutable subject identities and an expiry/invalidation policy.
9. Extensions cannot weaken core requirements or reinterpret core fields.
10. Secrets are referenced by opaque handles and never embedded in an HDP.
