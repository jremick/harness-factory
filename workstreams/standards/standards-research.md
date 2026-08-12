# Harness Definition Package: standards and existing-framework research

Status: research baseline  
As-of date: 2026-08-12  
Access date for every web source: 2026-08-12  
Method: standard, high-depth primary-source research with extended synthesis. Search results were used only for discovery; version and status claims were checked against official specifications, standards-body records, government publications, release records, repository snapshots, or the papers' primary records.

## 1. Executive finding

No reviewed source defines the complete HDP problem: an explicit, portable definition that connects purpose and requirements to a generated harness, model/provider/runtime/environment identity, independent evaluation, evidence custody, scoped assurance, and operational invalidation.

The strongest design is therefore a layered integration, not selection of one winner:

1. Use [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) as the normative structural grammar.
2. Use ISO/IEC/IEEE 29148 and NIST AI RMF/TEVV as requirements and risk/evaluation design authorities, without claiming conformance from this research alone.
3. Use SACM concepts to shape claims, evidence, and argument links while deferring the full metamodel.
4. Treat Agent Spec, Agent Spec Eval/Tracing, MCP, A2A, OpenAPI, OASF, and Agent Skills as versioned adapters or exchange surfaces, not the HDP root model.
5. Use natural-language and harness-engineering research as design hypotheses to test, not normative authority.
6. Keep HDP-original integration candidates explicit. They are original relative to this reviewed set, not a claim of global novelty.

## 2. Classification and status

| Class | Items | Status meaning for HDP |
|---|---|---|
| Formal standards | ISO/IEC/IEEE 29148:2018; OMG SACM 2.3 | Normative external authorities. A real conformance claim requires the full normative text, an exact profile/crosswalk, and evidence. |
| Mature or stable open industry specifications | JSON Schema 2020-12; OpenAPI 3.2.0 | Stable enough to adopt directly for bounded technical contracts. They are not substitutes for behavioral or assurance proof. |
| Government framework and guidance | NIST AI RMF 1.0; NIST AI 600-1; AIRC TEVV resources | Authoritative risk and TEVV guidance, but voluntary and non-prescriptive. AI RMF 1.0 is being revised. |
| Emerging open specifications and formats | Oracle Agent Spec/Eval/Tracing; Agent Skills; MCP; A2A; OASF | Useful interoperability surfaces with active version drift. Adopt by pinned adapter/profile. |
| Implementation guidance | Oracle `create-agent-spec` skill | Reusable authoring and validation procedure, not normative Agent Spec language. |
| Research frameworks | NLAH; Agentic Harness Engineering; Code as Agent Harness; From Prompts to Contracts; Model or Harness? | Testable ideas and evidence, mostly 2026 preprints. Do not use as conformance authorities. |
| HDP original-extension candidates | Resolution identity; evaluator custody; evidence contracts; scoped assurance; operational invalidation; cross-layer trace graph | Needed to bridge omissions across the reviewed sources. Must be marked as HDP-defined and validated through the reference implementation. |

## 3. Oracle Open Agent Specification ecosystem

### 3.1 Agent Spec

Current status has three distinct version surfaces:

- The latest stable package/repository release is [`agent-spec-26.1.2`](https://github.com/oracle/agent-spec/releases/tag/agent-spec-26.1.2), published 2026-06-02.
- Stable documentation installs `pyagentspec==26.1.2`, while the latest released Agent Spec language payload is `26.1.0` ([stable documentation](https://oracle.github.io/agent-spec/); [language specification](https://oracle.github.io/agent-spec/26.1.2/agentspec/language_spec_26_1_0.html)).
- Repository `main` at commit `d5633facba93fe3f2c593a70fe05bb8f031a6f49` carried [`VERSION=26.2.0.dev7`](https://github.com/oracle/agent-spec/blob/d5633facba93fe3f2c593a70fe05bb8f031a6f49/VERSION) on 2026-08-10. This is development state, not a stable release.

Classification: emerging open specification with a released SDK and runtime adapters.

Relevant HDP coverage:

- portable Agent and Flow representations;
- LLM/provider, tool, MCP, and A2A components;
- typed input/output schemas;
- structured flows, control nodes, and multi-agent patterns;
- JSON/YAML serialization, references, disaggregated components, and sensitive fields;
- adapters into concrete agent runtimes.

Omissions relative to HDP:

- purpose, users, outcomes, decision thresholds, and requirements lifecycle;
- the complete harness/runtime/environment/evaluator boundary;
- independent evaluator custody and hidden-fixture isolation;
- evidence provenance, integrity, retention, and assurance strength;
- scoped conformance/fitness claims and invalidation triggers;
- operational risk acceptance, monitoring, and incident/change history.

Recommendation: define an optional, versioned Agent Spec execution profile. An HDP generator may emit Agent Spec through PyAgentSpec and retain the output plus source/generator digests. Agent Spec must not become the canonical HDP definition because it is narrower and its package, language, and development versions move independently.

### 3.2 Oracle `create-agent-spec` skill

The released [`create-agent-spec/SKILL.md`](https://github.com/oracle/agent-spec/blob/agent-spec-26.1.2/.agents/skills/create-agent-spec/SKILL.md) was introduced on 2026-05-15 and is present in tag `agent-spec-26.1.2`.

Classification: implementation guidance packaged as an Agent Skill; not normative Agent Spec language.

Strong patterns to adapt:

- choose Agent versus Flow from the business structure;
- build through PyAgentSpec SDK classes;
- do not hand-write serialized Agent Spec artifacts;
- export through SDK APIs and round-trip validate;
- use typed input/output `Property` objects;
- keep secrets out of artifacts;
- require confirmation for write actions or external side effects;
- stop rather than fabricate output when the SDK is unavailable.

What not to adopt: the skill as an HDP conformance source, its Python-only availability as a core requirement, or its Agent-Spec-specific component selection as the whole harness model.

### 3.3 Agent Spec Eval

[Agent Spec Eval in stable 26.1.2 documentation](https://oracle.github.io/agent-spec/26.1.2/agentspec/evaluation.html) defines datasets, samples, metrics, evaluator orchestration, results, aggregators, retry behavior, repeated/ensemble metrics, intermediate caching, concurrency, and sensitive-data guidance.

Classification: released, emerging extension specification.

Fit:

- good adapter target for HDP datasets, metrics, and machine-readable result detail;
- separation of dataset, metric, and evaluator concerns is compatible with HDP;
- retry/repetition/ensemble support makes LLM-judge uncertainty visible when configured carefully.

Critical boundary: Agent Spec Eval's `Evaluator` abstraction is not sufficient proof of HDP evaluator independence. HDP must still keep final acceptance outside the generated harness, deny hidden-fixture access, version the evaluator separately, verify post-action state, and bind results to requirements and evidence.

Do not allow retries or aggregation to turn instability, missing results, or failed attempts into an unqualified pass. Preserve attempts, fallbacks, timing, token use, and uncertainty.

### 3.4 Agent Spec Tracing

[Agent Spec Tracing in stable 26.1.2 documentation](https://oracle.github.io/agent-spec/26.1.2/agentspec/tracing.html) defines Trace, Span, Event, SpanProcessor, correlation IDs, and standard events for LLMs, tools, agents, flows, nodes, state, exceptions, confirmations, and human-in-the-loop interactions.

Classification: released, emerging extension specification.

Recommendation: accept it as an observability input vocabulary and provide a versioned mapping into HDP observations. HDP must add:

- source/run/subject identity and immutable digests;
- evidence collection contract and completeness status;
- storage, retention, access classification, and custody;
- redaction result and policy version;
- links from observations to requirements, risks, measures, and claims;
- exporter-loss/back-pressure/error indicators.

Agent Spec's sensitive-field labels are directly useful, but traces contain prompts, tool I/O, messages, state, and errors. Masking must default closed. A span's existence is evidence of an observation, not proof that the operation was authorized, correct, complete, or successful.

## 4. Structural and interface specifications

### 4.1 JSON Schema

[JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) was published 2022-06-16 and remains the current published version on the official specification site.

Classification: mature open technical specification. Its Core and Validation documents have IETF Internet-Draft lineage, but Draft 2020-12 should not be mislabeled as an ISO standard or IETF RFC.

Adopt normatively for HDP L1 structural validation:

- pin `$schema` and stable absolute `$id` values;
- close core objects with `unevaluatedProperties: false` where intended;
- separate annotations from asserted validation behavior;
- bundle or digest-pin all normative references for offline validation;
- validate the HDP schema against the Draft 2020-12 meta-schema;
- ship positive and negative conformance fixtures;
- declare supported vocabularies and `format` behavior.

Do not use JSON Schema for cross-document meaning, implementation proof, outcome validation, authorization, evidence credibility, temporal expiry, or evaluator independence. Those belong to deterministic semantic rules and runtime/evaluator gates.

### 4.2 OpenAPI

[OpenAPI Specification 3.2.0](https://spec.openapis.org/oas/v3.2.0.html), dated 2025-09-19, is the latest published OAS.

Classification: stable open industry specification under the OpenAPI Initiative/Linux Foundation.

Fit: strong for HTTP tool, provider, runtime control, artifact, and evaluator interfaces. It covers operations, parameters, request/response content, servers, callbacks/webhooks, security schemes, and reusable schemas.

Important constraint: OAS 3.2 explicitly says its normative text is authoritative over the informational JSON Schema. Therefore an HDP cannot claim OpenAPI validity solely because an OAS schema validator passes.

Recommendation: reference OpenAPI documents by URI and digest, preserve `openapi` version, and map `operationId` into HDP tool/interface identifiers. Require capability declarations for the selected 3.2 validator/code generator. Do not silently downgrade to 3.1 or treat documented security schemes as proof of authorization enforcement.

## 5. Portable skills and agent interoperability

### 5.1 Agent Skills

The [Agent Skills specification](https://agentskills.io/specification) is an open living format originally developed by Anthropic. It defines a directory containing `SKILL.md` with YAML frontmatter and Markdown instructions, plus optional scripts, references, assets, metadata, compatibility, and experimental `allowed-tools`.

Classification: emerging living specification. The official repository had no tags or releases observed as of the access date; therefore `metadata.version: "1.0"` shown in an example must not be reported as the Agent Skills specification version.

Fit: strong for distributing the required portable HDP analysis/generation skill. Progressive disclosure is useful for keeping the core instructions compact and loading schema references or scripts only when needed.

Do not treat:

- skill instructions as machine-enforced authorization;
- `allowed-tools` as a security boundary without host enforcement;
- bundled scripts as safe without dependency pinning, review, and isolation;
- a valid `SKILL.md` as proof that its generated HDP or harness is correct.

The HDP skill needs its own explicit package version, compatibility range, dependency lock, output contracts, and deterministic validator calls because the underlying Agent Skills format is unnumbered and evolving.

### 5.2 MCP

The current released MCP revision is [`2026-07-28`](https://modelcontextprotocol.io/specification/2026-07-28), announced on 2026-07-28 in [the official release post](https://blog.modelcontextprotocol.io/posts/2026-07-28/). The release replaces the prior handshake/session model with a stateless core, adds `server/discover`, Multi Round-Trip Requests, header routing and caching, hardens authorization, moves tasks into an extension, and deprecates roots, sampling, logging, and legacy HTTP+SSE.

Classification: emerging open protocol with a dated compatibility revision.

Fit: strong for harness-to-tool/resource/prompt boundaries. MCP should appear in `tools` and `context` as a protocol binding, not as the definition of a harness.

Adopt with:

- pinned protocol revision and declared legacy compatibility;
- expected server identity/capabilities and schema digests;
- authorization issuer/audience/resource policy;
- HDP-owned data classification and least privilege;
- per-operation confirmation, idempotency/compensation, retry, timeout, and budgets;
- tool-description and result content treated as untrusted;
- trace/evidence mapping that does not expose credentials or sensitive payloads.

Uncertainty: an official general versioning page was observed lagging at `2025-11-25`, while the dated specification tree and release announcement expose `2026-07-28`. HDP should pin the actual dated revision URI rather than rely on an unversioned “latest/current” label.

### 5.3 A2A

The [A2A published specification](https://a2a-protocol.org/latest/specification/) labels `1.0.0` as the latest released protocol, while the repository's latest patch release is [`v1.0.1`](https://github.com/a2aproject/A2A/releases/tag/v1.0.1), published 2026-05-28. A2A negotiation uses major/minor `1.0`; specification patch numbers do not affect protocol compatibility.

Classification: emerging open protocol with a stable 1.0 family.

Fit: strong for communication across independent/opaque agents and trust boundaries. It covers discovery, Agent Cards, tasks, messages, parts, artifacts, multiple bindings, streaming, polling, push, multi-tenancy, and security declarations.

Recommendation: use A2A for external agent interfaces, not as the canonical description of internal orchestration. Bind Agent Card capability claims to HDP evidence and expiry. A valid Agent Card signature verifies the signed bytes against a key; authenticity still depends on trusted key-to-issuer binding, and neither fact proves the agent can safely or reliably perform the declared skill.

Risks include the breaking 0.3-to-1.0 migration, remote delegation authority, data propagation across organizational boundaries, version negotiation, and stale self-declared capabilities.

### 5.4 OASF

OASF is an AGNTCY schema system for agent records, skills/domains, modules, locators, and discovery ([official overview](https://docs.agntcy.org/oasf/open-agentic-schema-framework/)). The latest release is [`v1.1.0`](https://github.com/agntcy/oasf/releases/tag/v1.1.0), published 2026-07-10. The current [agent-record guide](https://docs.agntcy.org/oasf/agent-record-guide/) still shows `schema_version: 1.0.0` and Draft-07 validation, so official guide examples lag the release.

Classification: emerging open schema framework.

Fit: useful optional export for discovery metadata and capability taxonomy. Map HDP package identity, verified capability state, modules, and artifact locators into OASF where possible.

Do not import OASF skill declarations as verified HDP capabilities or assurance claims. Keep:

- the OASF schema version explicit;
- translation version and loss report;
- HDP source entity IDs and digests;
- self-asserted versus externally verified state;
- Draft-07 validation isolated from the HDP Draft 2020-12 validator.

OASF's validation API and generated JSON Schema have documented coverage differences; passing one validator is not necessarily equivalent to passing the other.

## 6. Requirements, risk, TEVV, and assurance

### 6.1 ISO/IEC/IEEE 29148

[ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html), Edition 2, was published 2018-11-28, confirmed current in 2024, and is now at stage 90.92 “to be revised,” with a committee draft under development.

Classification: formal international standard.

The public ISO record supports using it as an authority for requirements-engineering life-cycle processes, required information items, their contents, and formatting guidance. It is a strong fit for HDP purpose, stakeholder, requirement, interface, verification, assumption, and traceability structures.

Constraint: this workstream did not use the licensed full normative text. It must not assign clause-level conformance, reproduce normative requirements, or claim that HDP conforms to 29148. Before formalization, obtain authorized access, build a clause-by-clause crosswalk, identify tailoring, and validate the crosswalk with requirements-engineering expertise. The in-progress revision is a change watch item.

### 6.2 NIST AI RMF and TEVV

[NIST AI RMF 1.0 (NIST AI 100-1)](https://doi.org/10.6028/NIST.AI.100-1) was published 2023-01-26. NIST's [current program page](https://www.nist.gov/itl/ai-risk-management-framework) says AI RMF 1.0 is being revised. [NIST AI 600-1, the Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1), was published 2024-07-26. The [NIST AIRC](https://airc.nist.gov/) supports operationalization and TEVV resources.

Classification: government risk-management framework, companion profile, and resource guidance; not a conformance standard.

Adopt as a crosswalk:

- `governance`, roles, policies, and accountability → Govern;
- purpose, users, context, impacts, assumptions, dependencies, and risks → Map;
- measures, datasets, test methods, uncertainty, independent evaluation, monitoring → Measure;
- thresholds, treatments, approvals, incidents, stops, recovery, and reassessment → Manage;
- model/provider/runtime/environment snapshots and lifecycle gates → TEVV across the life cycle;
- provenance, pre-deployment testing, incident disclosure, and GAI-specific risks → NIST AI 600-1.

HDP should never reduce this to a compliance checkbox or single score. Profiles require context, risk tolerance, affected-party considerations, measurement limitations, and residual risk. Keep crosswalk identifiers non-normative and versioned because the RMF is under revision.

### 6.3 OMG SACM

[OMG Structured Assurance Case Metamodel 2.3](https://www.omg.org/spec/SACM/About-SACM) was adopted in October 2023. OMG publishes a normative PDF and normative machine-readable XML.

Classification: formal consortium standard.

Fit: conceptually strong for HDP claim, argument, evidence/artifact, terminology, citation, and assurance package exchange.

Recommendation for v0.1:

- use stable typed claim/evidence IDs;
- distinguish claims, reasoning/argument links, evidence artifacts, and citations;
- preserve support and refutation links;
- declare subject, scope, issuer, result, expiry, and invalidation;
- design a future SACM export mapping and record unmapped/lossy semantics.

Do not implement the full SACM metamodel merely for nominal alignment. A partial implementation must not be labeled SACM-conformant. HDP's runtime/evaluator custody, evidence integrity, and AI-specific measure semantics remain necessary additions.

## 7. Research frameworks

### 7.1 Natural-Language Agent Harnesses

[Natural-Language Agent Harnesses, arXiv:2603.25723v2](https://arxiv.org/abs/2603.25723v2), revised 2026-05-18, introduces editable NLAH policy documents and an Intelligent Harness Runtime that interprets them into agent calls, handoffs, state updates, validation gates, and artifact contracts.

Classification: research preprint, not a standard.

What to adopt:

- make harness control intent inspectable and reviewable;
- separate reusable policy from runtime-specific adapters;
- represent handoffs, state, validation, and artifact contracts explicitly;
- test portability and ablate modules independently.

What not to adopt:

- prose as the sole source of executable truth;
- model interpretation as an authorization mechanism;
- benchmark outcomes as proof of production fitness;
- implicit runtime behavior without a resolved, versioned artifact.

HDP can include natural-language policy as an explanatory or generator-input layer linked to typed controls. Machine-enforced permissions, schemas, budgets, stop rules, and evaluation thresholds remain authoritative.

### 7.2 AI harness engineering research

The reviewed 2026 primary research is converging on harnesses as a first-class system boundary, but it remains early and pre-standard:

- [Agentic Harness Engineering v4](https://arxiv.org/abs/2604.25850v4) uses component, experience, and decision observability and checks self-declared predictions against subsequent task outcomes.
- [Code as Agent Harness v1](https://arxiv.org/abs/2605.18747v1) frames code as operational infrastructure for interfaces, planning, memory, tools, feedback, verification, and multi-agent coordination.
- [From Prompts to Contracts v1](https://arxiv.org/abs/2607.08028v1) moves deterministic behavior into code, manifests, schemas, and validation artifacts, with fault injection and model-substitution experiments.
- [Model or Harness? v1](https://arxiv.org/abs/2607.28802v1) localizes failures across model, harness, user, tool, memory, environment, and grader interactions so repair responsibility is not assigned from output failure alone.

Research-informed HDP actions:

1. Inventory every editable harness component as a versioned artifact.
2. Treat each change as a falsifiable hypothesis with expected affected measures.
3. Preserve evidence before and after a change and require rollback metadata.
4. Use model-substitution and fault-injection tests to distinguish code-owned guarantees from model behavior.
5. Localize failures to interaction boundaries before changing the model or harness.
6. Gate self-evolution through independent evaluation, permission review, regression coverage, and scope controls.

Do not canonize reported benchmark gains, taxonomies, or automatic-evolution loops as HDP normative requirements. They are useful experimental designs whose external validity remains uncertain.

## 8. Coverage matrix by HDP field family

Legend: **P** primary coverage, **S** supporting/partial coverage, **-** outside normal scope.

| HDP field family | Agent Spec | Eval | Tracing | JSON Schema | Agent Skills | MCP | A2A | OpenAPI | OASF | 29148 | NIST | SACM | Research |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Identity/version/provenance | S | S | S | S | S | S | P | P | P | S | S | P | P |
| Purpose/users/outcomes | - | S | - | S | S | - | - | S | S | P | P | P | S |
| Requirements/assumptions | S | - | - | S | S | - | - | S | - | P | P | P | S |
| Model/provider configuration | P | S | P | S | - | - | - | S | S | - | S | - | S |
| Tools/context/interfaces | P | S | P | S | S | P | S | P | S | S | S | - | P |
| Orchestration/delegation | P | - | P | S | S | - | P | S | S | S | S | - | P |
| Runtime/environment/state | S | - | P | S | S | S | S | S | S | S | P | - | P |
| Permissions/approvals/budgets | S | - | P | S | S | S | S | S | - | S | P | S | P |
| Evaluation/TEVV | S | P | S | S | - | - | - | S | - | S | P | S | P |
| Trace/evidence capture | - | P | P | S | - | S | S | S | S | S | P | P | P |
| Claims/assurance/expiry | - | - | - | S | - | - | - | - | S | S | S | P | S |
| Change/drift/invalidation | S | S | S | S | S | S | S | S | S | S | P | S | P |

The matrix explains why the HDP root model must integrate multiple sources while retaining original fields.

## 9. HDP original-extension candidates

These candidates are original integrations relative to the sources reviewed here. They must be described as HDP-defined, not represented as clauses of another standard and not advertised as globally novel without a broader prior-art review.

### 9.1 Resolved subject identity

Define the assurance subject as a digest-bound tuple of HDP resolution, implementation, generator, model revision, provider configuration, runtime, tool adapters, policy, context snapshots, and evaluation plan. Existing formats identify pieces, but none reviewed makes the whole tuple the mandatory subject of a harness claim.

### 9.2 External evaluator custody contract

Define public evaluation contracts and opaque hidden fixture commitments in the HDP while keeping hidden content, answers, prompts, and labels in an evaluator-owned package inaccessible to the harness. Agent Spec Eval can implement metrics, but custody and authority remain HDP semantics.

### 9.3 Evidence contract above traces

Turn an observation into evidence only when it has subject identity, provenance, collection method/time, integrity, completeness status, access class, retention, and claim/requirement links. Agent Spec Tracing supplies event semantics; SACM supplies assurance concepts; HDP joins them operationally.

### 9.4 Typed intent-to-evidence trace graph

Require navigable paths from purpose/outcome to measure/threshold/evaluation/evidence and from requirement to control/verification/evidence/claim. JSON Schema validates node shapes; HDP semantic rules validate graph obligations.

### 9.5 Scoped claim lifecycle

Make conformance, fitness, outcome, control-effectiveness, and operational-assurance claims distinct. Bind each to a subject, profile, result state, evidence, issuer/reviewer, limitations, expiry, and invalidation triggers. Never collapse `unknown`, `not-run`, or `inconclusive` into pass.

### 9.6 Protocol-neutral policy overlay

Keep authorization, confirmation, data, idempotency, retry, budget, stop, recovery, and escalation policies outside MCP/A2A/OpenAPI/Agent Spec adapter documents. A binding can declare technical capability; HDP policy decides whether and how it may be used.

### 9.7 Translation and loss manifests

Every export to Agent Spec, OASF, SACM, OpenAPI, MCP configuration, or A2A metadata should state source/target versions, mapped entities, dropped or approximated semantics, generated artifact digests, and whether the loss affects execution or assurance.

## 10. Adoption decisions

| Decision | Recommendation | Reason |
|---|---|---|
| Structural schema | Adopt JSON Schema Draft 2020-12 normatively | Current, implementation-ready, and already selected by the project contract. |
| Canonical HDP model | Keep HDP-owned | No reviewed source spans requirements, complete harness identity, evaluator custody, and assurance. |
| Executable agent representation | Optional Agent Spec profile | Best direct coverage of portable agent/flow topology, but narrower and version-layered. |
| Evaluation adapter | Optional Agent Spec Eval mapping | Good metric/dataset abstractions; HDP must retain independent final authority. |
| Trace adapter | Optional Agent Spec Tracing mapping | Good event vocabulary; insufficient as an evidence ledger. |
| Tool/context protocol | Version-pinned MCP binding | Strong interface interoperability; authorization and tool safety remain HDP policy. |
| Inter-agent protocol | Version-pinned A2A binding | Use only at external/opaque agent boundaries. |
| HTTP contracts | OpenAPI 3.2.0 by reference/digest | Stable current API contract, with tooling capability check. |
| Discovery metadata | Optional OASF 1.1.x export | Useful taxonomy/registry surface, not a behavioral or assurance contract. |
| Portable skill | Agent Skills-compatible HDP skill | Cross-client distribution with HDP-owned version, validation, and dependencies. |
| Requirements authority | 29148 design alignment now; formal crosswalk later | Full licensed standard and revision monitoring are needed before conformance. |
| Risk/TEVV | NIST AI RMF/GAI crosswalk | Strong lifecycle and socio-technical coverage; keep voluntary/tailored status explicit. |
| Assurance model | SACM-inspired core, export later | Preserves a formal path without overloading v0.1. |
| Natural-language harness | Optional reviewed policy layer | Inspectability benefit without weakening deterministic enforcement. |
| Harness evolution | Research-informed gated experiment | Observability and falsifiability are valuable; self-editing must remain independently controlled. |

## 11. Key risks and unresolved questions

1. **Version pin granularity.** Agent Spec package, language payload, and development versions differ. A2A repository patch and negotiated protocol versions differ. OASF guide examples lag its release. HDP needs separate `specVersion`, `implementationVersion`, and `artifactDigest` fields.
2. **MCP status-page drift.** Pin the dated `2026-07-28` URI; do not resolve an unversioned “current” label at validation time.
3. **Schema dialect mismatch.** HDP and current Agent Spec property validation use Draft 2020-12, while OASF's guide uses Draft-07. Translation must identify dialect and loss.
4. **Normative access.** A clause-level 29148 mapping requires lawful access to the full standard. Public catalog text is not enough.
5. **SACM implementation depth.** Determine whether a real exchange partner needs SACM XML before taking on full metamodel complexity.
6. **Trace completeness.** Define how a run proves whether expected events were captured or dropped; tracing vocabularies alone do not solve this.
7. **Evaluator composition.** Define when deterministic, human, statistical, and LLM-based measures can be combined and how uncertainty/fallbacks affect pass/fail.
8. **Capability truth.** OASF records and A2A Agent Cards are declarations. Define evidence grades and expiry before surfacing “verified” capability.
9. **Translation equivalence.** Define minimum round-trip and semantic-loss tests for every adapter before describing portability.
10. **Research maturity.** Monitor revisions and peer-reviewed publication for the 2026 harness papers; do not freeze their benchmarks or taxonomies into the normative core.

## 12. Confidence and trust summary

The source register contains 28 primary/official entries. Version and publication claims are high confidence where official release or standards records exist. The following are moderate confidence or explicitly provisional:

- Agent Skills is an unnumbered living specification with no releases/tags observed.
- OASF documentation examples lag the current `v1.1.0` release.
- MCP's unversioned versioning page lagged the released dated specification.
- Research findings are supported by primary paper records but remain preprints and are not normative.
- ISO design alignment is based on the public catalog record, not the licensed normative clauses.

Machine-readable source details and concise evidence are in [`sources.json`](sources.json); the row-level adoption map is in [`standards-mapping.csv`](standards-mapping.csv).
