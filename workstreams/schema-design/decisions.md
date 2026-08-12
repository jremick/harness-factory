# Harness Definition Package: Architecture Decisions

Status: design draft
Decision statuses: `proposed`, `accepted-for-draft`, `superseded`, `rejected`

## HDP-ADR-001 — A package, not a monolithic document

- Status: accepted-for-draft
- Context: HDPs must cover intent, implementation, operations, evaluation, and assurance. A single schema becomes unreadable and creates unnecessary merge conflicts.
- Decision: Define independently valid modules indexed by one manifest and resolve them into one canonical graph.
- Alternatives: one large YAML file; unconstrained directory convention.
- Consequences: authors can own separate modules; validators need a resolver; cross-document semantic validation is mandatory.

## HDP-ADR-002 — Preserve a compact integrated projection

- Status: accepted-for-draft
- Context: Early generators expect stable top-level keys such as `purpose.intendedOutcomes`, `success.acceptanceCriteria`, `evaluation.tests`, and `orchestration.stages`.
- Decision: Define a deterministic single-document projection that preserves those keys while treating modular documents as authoritative source.
- Alternatives: force every generator to consume modules immediately; make the monolith authoritative.
- Consequences: integration can start early; the resolver must retain source-module/JSON-Pointer provenance; round-trip editing of the projection is deferred.

## HDP-ADR-003 — JSON Schema Draft 2020-12 is the structural contract

- Status: accepted-for-draft
- Context: The format needs standard tooling, recursive composition, discriminated modules, and strict validation.
- Decision: Publish JSON schemas using Draft 2020-12. YAML is an authoring serialization converted through a restricted YAML 1.2-to-JSON pipeline.
- Alternatives: bespoke validator; OpenAPI Schema; Protocol Buffers; CUE as the only source.
- Consequences: broad validation support; JSON Schema cannot enforce graph invariants or operational truth, so semantic and runtime layers remain separate.

## HDP-ADR-004 — Closed core with a single namespaced extension surface

- Status: accepted-for-draft
- Context: Silent typos and vendor-specific fields undermine portable conformance, while implementations need evolvability.
- Decision: Reject unknown core properties and allow extensions only under reverse-DNS namespaced keys with pinned schemas and explicit required/optional handling.
- Alternatives: open objects throughout; central approval for every extra field.
- Consequences: strict interoperability with bounded extensibility; unknown required extensions prevent conformance; extensions cannot weaken core/profile obligations.

## HDP-ADR-005 — Stable identity is separate from label and location

- Status: accepted-for-draft
- Context: Traceability and change analysis break when paths or display names are identity.
- Decision: Use global URI IDs for packages/top-level entities, compact package-scoped IDs for children, and typed reference objects with expected kinds.
- Alternatives: JSON Pointers only; file paths; free-text names.
- Consequences: reliable refactoring and graph analysis; authoring is more verbose; resolvers must report ambiguous and wrong-kind targets.

## HDP-ADR-006 — Resolved canonical graph is the assurance subject

- Status: accepted-for-draft
- Context: Imports, overlays, defaults, and mutable provider aliases make source YAML alone insufficient to identify what ran.
- Decision: Resolve offline, materialize defaults and selections, emit canonical JSON, and bind a digest to the complete resolved graph and referenced artifacts.
- Alternatives: hash source files; trust version labels.
- Consequences: reproducible validation and claims; resolver behavior becomes a versioned trusted component; mutable elements explicitly reduce reproducibility.

## HDP-ADR-007 — Validation is layered and preserves uncertainty

- Status: accepted-for-draft
- Context: Syntactic validity, coherent meaning, correct implementation, useful outcomes, and current operational assurance are different questions.
- Decision: Separate transport, structural, referential, semantic, profile, implementation, outcome, and operational-assurance checks. Preserve `not-run`, `not-applicable`, and `inconclusive`.
- Alternatives: one pass/fail validator; tests as the only proof.
- Consequences: claims become precise; reporting is more complex; a green structural validator cannot be presented as fitness evidence.

## HDP-ADR-008 — Evaluator is external to the harness

- Status: accepted-for-draft
- Context: A harness that can inspect or influence its judge can optimize for fixtures, leak answers, or fabricate self-reported success.
- Decision: An evaluator is never a harness role or tool. Evaluation uses a one-way contracted ingress and separately permissioned, versioned evaluator runtime.
- Alternatives: self-evaluation inside the harness; shared evaluation tool; prompt-only instruction not to inspect fixtures.
- Consequences: independent outcome evidence is stronger; local development requires a lighter logical boundary while production profiles require stronger separation.

## HDP-ADR-009 — Hidden evaluation material is referenced, never distributed

- Status: accepted-for-draft
- Context: A complete public package cannot safely include blind fixtures, answer keys, evaluator prompts, or scoring secrets.
- Decision: Public HDPs include opaque fixture-set IDs, pre-run digest commitments, custody/access/rotation policies, and evaluator contracts. Protected contents live in a separate evaluator-owned package.
- Alternatives: encrypt fixtures inside the HDP; rely on repository permissions; publish all tests.
- Consequences: leakage risk is reduced; validation can verify custody metadata but not fixture content; evaluators must attest to commitment and access controls.

## HDP-ADR-010 — Outcome validation is not model-judge-only

- Status: accepted-for-draft
- Context: Model judges can be useful but exhibit nondeterminism, shared blind spots, bias, and prompt/model version drift.
- Decision: Model judges are typed evaluators requiring pinned identity, calibration, uncertainty, segment analysis, and adjudication. Profiles may require deterministic or human-confirmed gates for critical measures.
- Alternatives: allow unqualified LLM-as-judge; ban model judges.
- Consequences: flexible evaluation without treating model scores as ground truth; additional calibration evidence is needed.

## HDP-ADR-011 — Profiles define cumulative conformance obligations

- Status: accepted-for-draft
- Context: One universal requirement set would either burden prototypes or under-specify production systems.
- Decision: Define cumulative base profiles (`core`, `development`, `controlled`, `production`, `high-assurance`) and orthogonal capability profiles.
- Alternatives: optional booleans; bespoke profiles with no inheritance; maturity score only.
- Consequences: scoped claims are comparable; profile governance and non-waivable rule lists must be versioned.

## HDP-ADR-012 — Traceability is a typed graph

- Status: accepted-for-draft
- Context: Embedded `tracesTo` arrays cannot express multi-hop paths, provenance, refutation, or change impact consistently.
- Decision: Use graph nodes plus controlled predicates such as `operationalizes`, `verifiedBy`, `validatedBy`, `measuredBy`, `mitigates`, `supports`, `refutes`, and `invalidatedBy`.
- Alternatives: per-object backreferences; external spreadsheet; requirements table only.
- Consequences: completeness and impact can be checked programmatically; tooling should render simpler matrices and views for humans.

## HDP-ADR-013 — Requirements and outcomes remain different concepts

- Status: accepted-for-draft
- Context: A harness can conform to implementation requirements yet fail its intended outcomes, or achieve an outcome through a non-conformant path.
- Decision: Requirements trace to implementation verification; outcomes trace to measures and independent validation. Claims can reference both but cannot collapse them.
- Alternatives: express outcomes as requirements; treat acceptance tests as all requirements.
- Consequences: conformance and fitness stay distinguishable; both trace paths are required.

## HDP-ADR-014 — Absence does not mean permission or safety

- Status: accepted-for-draft
- Context: Optional fields can accidentally become permissive defaults, especially for tools, data, budgets, and evaluation gaps.
- Decision: Use deny-by-default grants, explicit unknown records, bounded assumptions, exclusions, waivers, and risk acceptances. Missing decisions never imply pass.
- Alternatives: implementation defaults; schema defaults for policy.
- Consequences: packages are more explicit; minimal `core` still requires critical controls and outcome/evaluation intent.

## HDP-ADR-015 — Generic merge semantics are not normative overlays

- Status: accepted-for-draft
- Context: YAML merge keys and JSON Merge Patch cannot safely express protected values or whether a change strengthens or weakens an obligation.
- Decision: Profile/package overlays use typed operations against stable IDs and reject unauthorized weakening.
- Alternatives: YAML anchors; JSON Merge Patch; templating before validation.
- Consequences: safer composition and clearer provenance; overlay implementation is additional work and may be deferred from v1.

## HDP-ADR-016 — Secrets never enter the HDP

- Status: accepted-for-draft
- Context: Packages are copied, validated, signed, and retained as evidence; embedding credentials creates unacceptable exposure.
- Decision: Store only opaque secret handles and policy metadata. Runtime injects values through separately governed secret stores.
- Alternatives: encrypted values in package; environment interpolation.
- Consequences: packages remain distributable within their classification; execution validation needs runtime readback without revealing values.

## HDP-ADR-017 — Extensions cannot redefine conformance

- Status: accepted-for-draft
- Context: Vendor extensions could otherwise claim to override a core requirement or result meaning.
- Decision: Extensions may add fields and stronger obligations but cannot reinterpret, remove, or weaken core/profile semantics. Required unknown extensions fail conformance.
- Alternatives: allow vendor profile semantics; centralize all extensions.
- Consequences: portable core claims; extensions needing new semantics must propose a new core/profile version or a separately named capability claim.

## HDP-ADR-018 — Assurance expires and changes invalidate it

- Status: accepted-for-draft
- Context: Model aliases, context, providers, policies, data, runtime, and user populations drift after evaluation.
- Decision: Every assurance claim has an expiry and typed invalidation triggers. Production profiles define pinned baselines and reassessment scope for material changes.
- Alternatives: timeless certification; periodic review unrelated to change.
- Consequences: claims remain honest; monitoring and change ledgers are part of the assurance system.

## HDP-ADR-019 — Semantic rules are separately versioned

- Status: proposed
- Context: JSON Schema cannot express cross-document graph, subset, trace-path, independence, or evidence freshness rules.
- Decision: Publish semantic rule sets separately from structural schemas and bind each validation report to an exact rule-set and validator digest. The draft uses a side-effect-free CEL-derived environment.
- Alternatives: hard-code rules in one validator; use general-purpose scripts; encode graph rules in SHACL.
- Consequences: rule evolution is auditable; an executable function contract is needed before interoperability claims.

## HDP-ADR-020 — Evidence is metadata-rich and content-minimizing

- Status: accepted-for-draft
- Context: Auditability requires provenance and integrity, while privacy and fixture protection argue against copying raw content into traceability records.
- Decision: Evidence records carry subject, producer, collection, digest/signature, custody, classification, retention, and an access-controlled location reference. Claims disclose only necessary evidence views.
- Alternatives: embed logs/results; record only a URL.
- Consequences: stronger integrity and privacy posture; evidence stores and access policies are external dependencies.

## Unresolved decisions

| ID | Question | Impact if unresolved | Owner suggestion | Blocking |
|---|---|---|---|---|
| HDP-Q-001 | What permanent domain/URI authority owns `$id` and ontology namespaces? | Published identities could later move. | Specification governance | Yes for public release |
| HDP-Q-002 | Which canonical JSON and signature envelope are mandatory? | Different resolvers can produce different digests. | Schema + security workstreams | Yes for signed claims |
| HDP-Q-003 | Is the semantic-rule language a restricted CEL environment, SHACL, Rego, or validator API only? | Interoperable semantic results cannot yet be guaranteed. | Schema implementers | Yes for validator conformance |
| HDP-Q-004 | Are authored overlays in v1, or only explicit resolved packages? | Complexity and generator schedule. | Package/tooling leads | No for first schema |
| HDP-Q-005 | Which profile rules are non-waivable? | Conformance strength and governance. | Assurance governance | Yes for profile publication |
| HDP-Q-006 | What minimum evaluator separation is required per profile? | Local feasibility versus leakage/independence. | Evaluation + security workstreams | Yes for controlled+ |
| HDP-Q-007 | How are hidden fixture commitments disclosed without enabling inference? | Auditability can conflict with secrecy. | Evaluation custody owner | Yes for hidden evaluation |
| HDP-Q-008 | What minimum evidence store guarantees are portable? | Operational-assurance claims may not be comparable. | Evidence/observability leads | Yes for production |
| HDP-Q-009 | Which vocabulary registries are centrally governed? | Packages may diverge on units, risk ratings, and relation predicates. | Specification governance | No for alpha |
| HDP-Q-010 | Does `runtime.profile` identify a conformance profile, a deployment profile, or both? | Existing generator naming can conflate policy with runtime target. | Generator integration owner | Yes for final schema |
| HDP-Q-011 | Which legal/compliance sources may be referenced but not redistributed? | Packaging and license risk. | Legal/compliance owner | No for core |
| HDP-Q-012 | What privacy-preserving evidence disclosure is sufficient for external audit? | Evidence can expose users, prompts, or blind fixtures. | Privacy + assurance owners | Yes for high-assurance |
