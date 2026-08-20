# HDP 0.1 authoring guide and field reference

Author in YAML, validate against the canonical JSON data model, and generate
only after semantic validation succeeds.

## Authoring sequence

1. Copy [`examples/minimal/hdp.yaml`](../examples/minimal/hdp.yaml) only for a
   new authored HDP in the same controlled profile. Do not use a domain example
   to reconstruct an unrelated existing harness.
2. Define intended users and externally meaningful outcomes before harness
   mechanics. Each outcome needs a measure and hard or soft threshold.
3. Add atomic requirements with stable IDs, rationale, priority, status, and
   verification IDs.
4. Declare environment, task distribution, assumptions, dependencies, and
   exclusions. State what happens when each material assumption is false.
5. Define model capabilities and provider/routing constraints without embedding
   credentials or assuming mutable aliases are reproducible.
6. Define inputs, outputs, artefacts, context sources, tools, roles, stages,
   state, permissions, approvals, budgets, stops, failures, and telemetry.
7. Define the public evaluation contract. Keep private cases and evaluator code
   outside the HDP and generator input; store only opaque IDs and digest
   commitments.
8. Complete outcome-to-requirement-to-component-to-test-to-evidence edges.
9. Record compatibility, change control, limitations, residual risks, and drift
   triggers.
10. Run structural and semantic validation before generation.

## Top-level field reference

| Field | Required authoring question |
| --- | --- |
| `hdpVersion`, `kind` | Which vocabulary and document kind is this? |
| `metadata` | Who owns this version, and where did its facts come from? |
| `purpose` | Who should experience what externally meaningful outcome? |
| `operationalContext` | Which tasks, environments, assumptions, dependencies, and exclusions bound the claim? |
| `success` | How is each outcome measured and what threshold decides acceptance? |
| `requirements` | What MUST/SHOULD/MAY hold, why, and how is it verified? |
| `models` | Which capabilities, providers, regions, revisions, routing, and fallbacks are allowed? |
| `contracts` | What inputs, outputs, artefacts, schemas, classifications, and custody rules apply? |
| `context` | Which sources are authoritative, fresh, ordered, bounded, and conflict-resolved? |
| `tools` | Which callable interfaces/external systems exist and what side effects can they cause? |
| `orchestration` | Which roles and bounded stages act, delegate, stop, and hand off? |
| `state` | What working state and durable memory exist, where, for how long, and under whose authority? |
| `governance` | Which paths/tools/data are allowed or denied and which actions require approval? |
| `resources` | What token/cost/time/tool/rate budgets and stop conditions bound execution? |
| `failures` | How are failures classified, detected, recovered, retried, and escalated? |
| `observability` | Which events, correlations, redactions, interventions, and retention produce evidence? |
| `safety` | Which security, privacy, safety, and compliance constraints apply and how are they checked? |
| `evaluation` | Which public contracts, protected fixtures, scenarios, metrics, evaluators, and negative/adversarial/regression tests decide outcomes? |
| `runtime` | Which target profile, OS/runtime/dependency lock, sandbox, and deployment environment apply? |
| `monitoring` | Which baselines, drift rules, alerts, and reassessment triggers keep claims current? |
| `traceability` | Can every outcome reach requirement, component, test, and evidence? |
| `evolution` | What is compatible, breaking, deprecated, migrated, reviewed, and regression-gated? |
| `limitations`, `risks` | What remains unproven or residual after treatment? |
| `extensions` | Which namespaced non-core semantics are required, and can consumers safely preserve them? |

Detailed types and constraints are normative in
[`hdp.schema.json`](../src/hdp/schemas/hdp.schema.json). Extended design-level
field semantics are documented in
[`schema-design.md`](../workstreams/schema-design/schema-design.md).

## Stable identifiers

Use uppercase stable IDs such as `REQ-PROCESS-VERIFY`, `TEST-EXTERNAL`, and
`ARTIFACT-EVIDENCE`. Labels and file paths are not identity. Do not reuse an ID
for a different concept. Reference resolution is package-local in v0.1 and has
no implicit network lookup.

## Requirements language

Use MUST for mandatory behavior, SHOULD for a recommended behavior with a
justifiable exception, and MAY for an option. Keep one independently verifiable
obligation per requirement record. A MUST requirement MUST be `accepted` before
generation and MUST reference at least one test.

## Evaluation and evidence

The HDP may describe hidden material only through an opaque fixture/test record
and digest commitment. It MUST NOT contain the private contents. Deterministic
evaluators are preferred. An LLM judge requires a rubric, pinned model/provider
identity, repetitions, aggregation, uncertainty, and an adjudication policy.

Generated self-tests verify implementation but do not decide independent
acceptance. Evidence records should bind command/action, actor, timestamp,
subject/run ID, exit status, logs, digests, requirement IDs, and any skipped or
inconclusive state.

## Commands

```bash
uv sync --frozen --python 3.12
uv run hdp validate examples/software-development/hdp.yaml --json
uv run hdp compile examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml \
  --output <empty-directory>
```

Generation refuses structurally or semantically invalid input, unresolved MUST
requirements, unsupported target profiles, non-empty unmanaged directories, and
manual edits to generated files. Put human extensions under `manual/`.

The alpha packager releases only the exact manifest-owned generated tree. A
`manual/` extension may be retained during iterative compilation, but it must be
promoted into a declared/generated artifact before release packaging; otherwise
packaging fails closed.
