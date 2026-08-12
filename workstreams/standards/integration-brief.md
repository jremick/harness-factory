# HDP standards integration brief

As of: 2026-08-12  
Decision audience: HDP schema, generator, evaluator, and assurance implementers

## Recommended architecture

Keep one HDP-owned canonical model and integrate external specifications through versioned, digest-bound profiles and adapters.

```text
Purpose / requirements / risk / assurance          HDP-owned canonical definition
                     |
          Draft 2020-12 structural schema           normative L1 validation
                     |
     deterministic reference and semantic rules    normative L2-L4 validation
                     |
  Agent Spec | MCP | A2A | OpenAPI | OASF exports  optional versioned adapters
                     |
        harness + runtime + environment             identified execution subject
                     |
       Agent Spec Tracing or other telemetry        observations
                     |
        external evaluator and hidden custody       authoritative outcome judgment
                     |
           evidence and assurance graph             scoped, expiring claims
```

## Decisions to take now

1. **Normatively adopt JSON Schema Draft 2020-12.** Pin `$schema`/`$id`, validate the schema against the meta-schema, keep core objects closed, bundle or digest-pin references, and maintain positive/negative fixtures. Do not encode cross-document or runtime meaning as if JSON Schema could prove it.

2. **Keep HDP canonical and protocol-neutral.** Agent Spec is the strongest executable interchange candidate, but it does not cover HDP purpose, requirements, evaluator custody, evidence integrity, or assurance. Generate Agent Spec as an optional artifact rather than replacing the HDP definition.

3. **Implement the Agent Spec adapter against stable versions.** Target PyAgentSpec `26.1.2` and language `26.1.0`; record both. Treat `26.2.0.dev7` as development-only. Follow Oracle's `create-agent-spec` guidance: construct through the SDK, export through the SDK, round-trip validate, exclude secrets, and require confirmation for side effects.

4. **Keep the evaluator external even when using Agent Spec Eval.** Agent Spec Eval can implement datasets and metrics. Final acceptance remains evaluator-owned and independently versioned, with hidden fixtures unreachable by the harness. Preserve all attempts, fallbacks, timing, tokens, and uncertainty.

5. **Accept Agent Spec Tracing as one trace vocabulary, not as the evidence ledger.** Add subject digests, provenance, completeness, redaction, custody, retention, integrity, and requirement/claim links in the HDP evidence layer.

6. **Pin interface protocols independently.** Use MCP `2026-07-28` for tool/context bindings, A2A negotiated `1.0` with implementation release `1.0.1` for external agent boundaries, and OpenAPI `3.2.0` for HTTP contracts. Never infer authorization, safety, or business approval from a protocol document alone.

7. **Make OASF and Agent Skills distribution surfaces.** Export OASF `1.1.x` discovery records with translation-loss metadata. Package the HDP authoring/analysis workflow as an Agent Skills-compatible skill with its own version and dependency lock. Neither surface is an assurance authority.

8. **Align governance, requirements, and assurance deliberately.** Use ISO/IEC/IEEE 29148 for requirements-process alignment, NIST AI RMF/GAI Profile for risk and life-cycle TEVV crosswalks, and SACM 2.3 concepts for claims/evidence. Defer any formal conformance statement until a full licensed/normative crosswalk and evidence profile exist.

9. **Use harness research to shape tests.** Include component inventories, change hypotheses, fault injection, model substitution, interaction-level failure ownership, and rollback evidence. Natural-language harness policy may be a reviewed explanatory layer; machine contracts remain authoritative.

## Version ledger

| Surface | Pin now | Status note |
|---|---|---|
| HDP structural schema dialect | JSON Schema `2020-12` | Current published draft, 2022-06-16. |
| Oracle Agent Spec SDK | `26.1.2` | Latest stable release, 2026-06-02. |
| Oracle Agent Spec language | `26.1.0` | Latest released language payload in stable docs. |
| Oracle Agent Spec development | `26.2.0.dev7` | Main snapshot on 2026-08-10; do not use for stable conformance. |
| MCP | `2026-07-28` | Current released dated revision; stateless modern era. |
| A2A | protocol `1.0`; repo `v1.0.1` | Patch does not participate in protocol negotiation. |
| OpenAPI | `3.2.0` | Latest published OAS, 2025-09-19. |
| OASF | `v1.1.0` | Latest release, 2026-07-10; guide examples still show 1.0.0. |
| Agent Skills | pin source commit and HDP skill version | Living, unnumbered spec; no releases/tags observed. |
| ISO/IEC/IEEE 29148 | `2018`, Edition 2 | Current but “to be revised”; monitor committee draft. |
| NIST AI RMF | `1.0` and NIST AI `600-1` | RMF 1.0 is being revised. |
| OMG SACM | `2.3` | Latest formal version listed by OMG. |

## Adapter contracts

Every adapter/export should emit a deterministic manifest with:

- source HDP specification/package/resolution versions and digest;
- target specification and implementation versions;
- adapter identity, version, configuration, and digest;
- mapped entity IDs;
- dropped, approximated, or runtime-defined semantics;
- output artifact paths/media types/digests;
- validation commands and results;
- whether any loss affects execution, evaluation, or assurance;
- unresolved prerequisites and mutable dependencies.

Minimum adapter-specific checks:

| Adapter | Required check |
|---|---|
| Agent Spec | SDK construction/export, round-trip load, declared language version, runtime-adapter capability matrix, no secret values. |
| Agent Spec Eval | Metric input mapping, failure/fallback semantics, concurrency, result detail custody, evaluator-boundary test. |
| Agent Spec Tracing | Expected event coverage, dropped-event reporting, sensitive-field redaction, correlation, evidence-ingest mapping. |
| MCP | Protocol revision, discovery/capability match, auth issuer/resource binding, tool schema validation, approval/idempotency policy. |
| A2A | Negotiated version, Agent Card signature verification, capability evidence/expiry, tenant and delegation boundary. |
| OpenAPI | OAS version, normative validation/lint, reference closure, operation-ID mapping, security declaration versus enforcement distinction. |
| OASF | Schema version, Draft-07 isolation, validation route used, self-asserted/verified marker, taxonomy and translation-loss report. |
| SACM | Mapping profile version, unmapped constructs, package/claim/evidence identity, no SACM conformance claim for partial export. |

## HDP-original integration candidates

Treat these as explicit HDP vocabulary, with provenance to influencing sources but no false attribution:

- resolved model-harness-runtime-environment-evaluator subject identity;
- public evaluation contract plus separate hidden-fixture custody contract;
- evidence contract above raw traces;
- typed purpose-to-outcome and requirement-to-evidence trace graph;
- scoped claim states, expiry, and invalidation;
- protocol-neutral permission, approval, idempotency, budget, stop, recovery, and escalation policy;
- translation and semantic-loss manifests.

These are the main reason not to adopt Agent Spec, OASF, SACM, or any one protocol as the root HDP schema.

## Risks requiring tests

| Risk | Required proof |
|---|---|
| Version labels resolve to different layers | Fixture with distinct spec, SDK, adapter, package, and artifact digest fields; reject ambiguous `latest`. |
| Adapter claims portability but drops behavior | Round-trip/semantic-loss test plus cross-runtime scenario where available. |
| Traces are incomplete or leak data | Missing-event/exporter-failure tests and field-level redaction tests. |
| Evaluator is reachable from the harness | Filesystem, network, tool-registry, retrieval-index, and prompt leakage tests. |
| OASF/A2A claims are mistaken for proven capability | Require verification state, evidence grade, issuer, expiry, and downgrade unverified claims. |
| LLM judge instability is hidden by retry/aggregation | Preserve raw attempts and compute uncertainty; explicit policy for fallback and inconclusive. |
| Natural-language policy bypasses controls | Negative tests proving runtime permissions and stops win over prose. |
| Self-evolving harness widens authority | Diff policy, independent evaluation, permission regression, rollback, and human approval for authority changes. |
| Formal standards alignment is overstated | Lint claims for named version/profile/scope/evidence and prohibit “compliant” without an approved crosswalk. |

## Open decisions

1. Is SACM export required for a known consumer in v0.1, or is a future-compatible claim graph sufficient?
2. Which OpenAPI 3.2 validators/code generators are admitted by the reference profile, and what is the fallback when tooling only supports 3.1?
3. Does the Agent Spec adapter target only the stable 26.1.0 language, or also provide an explicitly experimental 26.2 profile?
4. What is the minimum trace-completeness signal when processors fail asynchronously?
5. Which evaluator combinations can issue a `pass` versus only `inconclusive` when an LLM-based judge is involved?
6. What evidence threshold upgrades an OASF skill or A2A Agent Card capability from self-asserted to verified?
7. Who obtains the licensed ISO/IEC/IEEE 29148 text and owns the future clause-level crosswalk?
8. What change triggers invalidate operational assurance: model alias movement, provider policy change, tool schema change, evaluator change, or all of these?

## Acceptance implications for v0.1

The v0.1 reference should not be declared complete on source/schema output alone. A defensible acceptance run includes:

1. Draft 2020-12 meta-schema and instance validation.
2. Deterministic semantic failures for missing outcomes, unresolved references, mutable identities, permission gaps, and untraceable requirements.
3. Agent Spec generation/round-trip validation if that profile is selected.
4. Protocol/interface contract checks for any declared MCP, A2A, or OpenAPI binding.
5. A clean execution with model, provider, harness, runtime, tools, policy, and context identities recorded.
6. Trace capture with completeness/redaction results.
7. External evaluation with protected-fixture leakage tests.
8. Evidence-to-claim graph validation with expiry/invalidation fields.
9. Adapter semantic-loss reports and honest `not-run`/`inconclusive` states.

Detailed evidence is in [`standards-research.md`](standards-research.md), [`sources.json`](sources.json), and [`standards-mapping.csv`](standards-mapping.csv).
