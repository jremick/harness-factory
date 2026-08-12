# HDP Schema-Design Integration Brief

Status: ready for integration review; design drafts only

## Outcome

This workstream defines a modular Harness Definition Package architecture that covers intended outcomes, operating context, harness generation, structural and semantic validation, execution controls, independent outcome evaluation, operational monitoring, and auditable traceability.

The design supports two compatible views:

1. **Authoring package**: specialized YAML modules indexed by `hdp.yaml`.
2. **Resolved projection**: one canonical top-level object for generators and validators.

The resolved projection preserves the integration keys already expected by the generator: `metadata`, `purpose.intendedOutcomes`, `operationalContext.assumptions`, `success.acceptanceCriteria`, `requirements`, `governance.permissions`, `resources.stoppingConditions`, `failures.recoveryPolicies`, `evaluation.tests`, `evaluation.boundary`, `evaluation.metrics`, `runtime.profile`, `orchestration.roles`, `orchestration.stages`, and `traceability`.

## Deliverables

| File | Integration value |
|---|---|
| `conceptual-model.md` | Precise definitions, system/trust boundaries, assurance vocabulary, entity relations, lifecycle gates, claims, and foundational invariants |
| `information-architecture.md` | Modular package layout, complete field-family map, resolution/composition, YAML normalization, profiles, traceability, extensions, versioning, and evaluation custody |
| `schema-design.md` | Draft 2020-12 schema distribution, common types, manifest sketch, concrete integrated YAML skeleton, module field design, generation binding, evaluator isolation, and claim shape |
| `semantic-rules.yaml` | 62 proposed cross-document rules spanning identity, outcomes, requirements, execution, tools, delegation, governance, budgets, recovery, telemetry, safety, evaluation, deployment, drift, evidence, change, and risk |
| `ontology.yaml` | Core entity classes, typed relations, controlled vocabularies, and invariants |
| `decisions.md` | 20 ADR-like decisions and 12 unresolved governance/schema questions |
| `integration-brief.md` | This handoff: findings, evidence, risks, and recommended next actions |

## Key findings

### 1. Structural validity is only the first gate

JSON Schema can validate document shape but cannot establish cross-document coherence, correct harness implementation, achieved outcomes, or current operational fitness. The package therefore separates:

- transport and structural validation;
- reference and semantic verification;
- profile conformance;
- implementation verification;
- independent outcome validation; and
- operational assurance.

Every report preserves `not-run`, `not-applicable`, and `inconclusive`; none can become `pass` implicitly.

### 2. The evaluator must be outside the harness trust boundary

The evaluator is not a harness role or tool. Public HDPs carry only opaque hidden-fixture references, prior integrity commitments, custody metadata, metric definitions, and evaluator interfaces. Hidden fixtures, answers, judge prompts, and scoring secrets stay in a separately permissioned evaluator package and runtime.

This is both a schema constraint and an operational control. Declared separation does not prove actual isolation; production evidence must include permission/runtime readback and leakage controls.

### 3. Conformance and fitness are different claims

Conformance asks whether a pinned subject satisfies a named HDP version and profile. Fitness asks whether the subject is suitable for a named purpose and operating envelope. Operational assurance is a time-bounded claim that combines both with runtime, monitoring, change, and incident evidence.

The distinction prevents a structurally valid or requirement-conformant harness from being presented as useful or safe without outcome evidence.

### 4. Traceability must be a typed graph

Every mandatory requirement reaches a verification method and expected evidence. Every outcome reaches a measure, threshold/decision rule, evaluation scenario, evaluator, and evidence contract. Evidence explicitly `supports` or `refutes` claims. Changes, drift, and incidents can invalidate claims.

### 5. Reproducibility requires a resolved subject tuple

Source YAML or a package version is insufficient. Claims bind the resolved HDP digest, harness implementation, generator, model revision, provider configuration, runtime, tools, policies, context snapshots, and evaluation plan. Mutable aliases are permitted only with observed resolution evidence and reduced reproducibility claims.

## Coverage evidence

The required field families are mapped one-for-one in `information-architecture.md` and expanded into proposed schema fields in `schema-design.md`:

| Coverage group | Included families |
|---|---|
| Intent and operation | identity/provenance; purpose/users/outcomes; environments/tasks/scenarios; assumptions/dependencies/exclusions; measures/thresholds; requirements |
| Harness construction | model/provider constraints; I/O/artifact contracts; context/knowledge; tools/interfaces; control/orchestration/roles/delegation; state/memory/lifecycle |
| Governance and reliability | permissions/data/approvals; budgets/time/rates/stops; failures/recovery/escalation; observability/tracing/interventions; safety/security/privacy/compliance |
| Evaluation | datasets/scenarios/fixtures/metrics/evaluators; negative/adversarial/regression; evaluator boundary; leakage controls; result policies |
| Operation and assurance | runtime/deployment; monitoring/drift; traceability/evidence/claims; change/compatibility/deprecation; limitations/risks/open questions |

The design also defines generation, structural validation, semantic verification, implementation verification, outcome validation, conformance, fitness, outcome, and operational assurance explicitly in `conceptual-model.md`.

## Validation evidence

Performed in the repository on 2026-08-12:

- Ruby Psych safe-loaded `semantic-rules.yaml` with aliases disabled: pass.
- Ruby Psych safe-loaded `ontology.yaml` with aliases disabled: pass.
- PyYAML 6.0.3 safe-loaded both YAML files with a custom duplicate-key rejection constructor: pass.
- Semantic rule IDs are unique (62); ontology class/relation IDs are unique (97): pass.
- `git diff --check -- hdp-reference/workstreams/schema-design`: pass.
- Targeted key scan confirmed every generator integration key listed above is present in the concrete skeleton and mapping table: pass.

Not performed:

- JSON Schema meta-validation, because this workstream intentionally proposes schema design and sketches rather than emitting final `.schema.json` artifacts.
- Execution of semantic expressions, because the HDP-CEL function environment is not yet an implemented standard.
- Runtime or evaluator-isolation testing, because there is no harness/evaluator implementation in this workstream.

## Integration risks

| Risk | Impact | Recommended treatment |
|---|---|---|
| The semantic expression environment is proposed, not executable | Different validators could interpret rules differently | Decide CEL subset versus SHACL/Rego/validator API; publish function conformance tests |
| URI authority, canonical JSON, and signature envelope are undecided | IDs/digests may not interoperate | Resolve before public schema or signed claims |
| `runtime.profile` may conflate conformance and deployment profiles | Generators may apply the wrong defaults | Preserve the key for compatibility but decide whether it aliases `profiles.base` or contains a separate runtime target ID |
| Modular-to-integrated projection is one-way in v1 | Editing generated projections can lose provenance | Declare projection read-only and keep modular source authoritative |
| Declared evaluator separation can be false at runtime | Hidden-fixture leakage and invalid evaluation | Require permission/network/readback evidence and canary/leakage tests in controlled+ profiles |
| Strict required fields can overburden prototypes | Authors may bypass the format | Keep `core` small but never optionalize evaluator boundary, outcomes, hard execution bounds, or trace paths |
| Extension schemas can fragment vocabulary | Weak portability and misleading claims | Registry rules, reverse-DNS ownership, digest pins, and non-weakening validation |
| Evidence may expose sensitive prompts, users, or fixtures | Privacy and evaluation integrity harm | Store content externally; include only integrity/provenance metadata and access-controlled references |
| Model/provider identifiers may be mutable or ambiguous | Results are not reproducible | Prefer immutable revisions; otherwise record observed metadata and downgrade claims |
| Profiles and waivers lack a governance authority | Conformance strength can drift | Version profile rule sets and publish protected/non-waivable rule IDs |

## Recommended integration action

1. Adopt the integrated top-level skeleton in `schema-design.md` as the alpha generator contract, preserving its exact key names.
2. Select one minimal vertical slice—manifest, purpose/outcomes, tasks, requirements, tools/permissions, budgets/stops, evaluation boundary/tests/metrics, runtime profile, and traceability—and emit real Draft 2020-12 schemas for it.
3. Implement L0–L3 validation first: safe YAML load, structural schema validation, typed reference resolution, and a small protected semantic rule set.
4. Make these initial semantic rules non-waivable: typed-reference integrity, outcome-to-evaluation trace, requirement-to-evidence trace, bounded execution, no embedded secrets, evaluator exclusion from harness roles/tools, hidden-fixture isolation, and non-pass uncertainty states.
5. Define a separate evaluator package/interface before adding hidden fixtures. Do not place hidden contents under the HDP package tree.
6. Resolve the blocking ADR questions for namespace authority, canonicalization/signing, semantic-rule execution, evaluator separation, profile governance, and `runtime.profile` meaning.
7. Add conformance fixtures: minimal valid package, each structural failure, broken typed reference, missing trace path, permission escalation, unbounded loop, fixture leakage, stale evidence, and breaking change without migration.

## Scope boundary

These files are design inputs for integration. They are not final schemas, a validator, a generator, a runtime, an evaluator, or a conformance claim. The strongest verified statement is that the two YAML design artifacts parse successfully and the documented design covers the requested field families and established generator keys.
