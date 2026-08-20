---
name: analyse-existing-harness
description: Inspect an existing AI or coding-agent harness and reconstruct an evidence-annotated Harness Definition Package (HDP), preserving observed behavior, declared intent, inference, uncertainty, omissions, contradictions, confidence, and human-confirmation needs. Use for AGENTS.md, prompts, Agent Skills, Agent Spec, MCP/tool configuration, orchestration code, hooks, memory/context logic, permissions, evaluators, tracing, CI/CD, runtime, or deployment controls.
---

# Analyse an existing harness

Reconstruct what the artifacts support. Never convert implementation mechanics
into invented business outcomes or assurance claims.

## Workflow

1. Establish the harness root, analysis output directory, access boundary, and
   whether runtime observation is authorized. Keep output outside the subject.
2. Run `scripts/inventory_harness.py HARNESS --output inventory.json`. Review
   symlinks, oversized files, likely secrets, binary files, and skipped paths
   before opening content. Do not print secret values.
3. Inspect relevant artifacts in this order:
   - system/developer prompts and `AGENTS.md` equivalents;
   - Agent Skills and Agent Spec agent/flow documents;
   - tool, MCP, A2A, OpenAPI, and provider configuration;
   - orchestration, hooks, middleware, state, memory, and context code;
   - permission/sandbox policy and human approval gates;
   - evaluators, tests, traces, CI/CD, runtime, deployment, and operating docs.
4. Run `uv run hdp analyse HARNESS --output ANALYSIS`. If
   `.hdp/source-definition.public.json` exists, this performs exact
   declared-source recovery; still compare it
   against observable artifacts for drift and contradictions.
5. Otherwise author a candidate against `references/hdp.schema.json`. Do not use
   a domain example as a scaffold. Populate only evidence-supported values. Copy
   declared scalar and prose values exactly when the schema permits. A mapped
   string MUST preserve the complete source string, including qualifiers such as
   frequency, retention scope, actor, and time horizon; do not prepend a label,
   shorten the value, or paraphrase merely to normalize wording. If the schema cannot represent a
   required unknown honestly, omit that field, retain the structural diagnostic,
   and record the unknown in the report rather than fabricating a value merely to
   pass validation. For a typed atomic field such as a duration, enum, identifier,
   digest, or media type, extract the exact atomic source value rather than copying
   its surrounding sentence. For a free-text field, map one complete source
   assertion and do not shorten it, split a coordinated list into multiple claims,
   or concatenate an adjacent governance, limitation, or outcome sentence. A
   free-text field whose name suggests one component, such as
   `expectedFrequency`, still receives the complete declared source scalar unless
   the source exposes that component as its own atomic value. When one source
   sentence declares multiple typed values for different target fields, extract
   only the exact atomic value governed by the selected field and map or
   explicitly omit each adjacent value separately. For example, a trace-retention
   field receives the trace-retention duration, not the coordinated aggregate
   result-retention clause. When the schema expects a subject phrase rather than
   declarative framing, remove the exact subject-and-copula frame. If the target
   is a standalone statement, change only the first remaining alphabetic
   character to sentence case; otherwise preserve the remaining phrase byte for
   byte. For example, `The target operator is a reliability engineer.` maps to
   `A reliability engineer.` rather than a new sentence about the operator.
   Preserve the source phrase's determiner and punctuation. Classify a target-user or intended-outcome statement as intent,
   not operational behavior. Add stable IDs and trace links without claiming that
   an ID proves a fact.
6. Build a source-to-HDP coverage table before authoring prose. For every
   structured scalar and every policy-list item, record its target pointer or an
   explicit omission. Apply these direct mappings when present:
   - declared input/output contracts and their media types map to matching
     `contracts.inputs` or `contracts.outputs`; a path-bearing output may also be
     an artifact, but the artifact mapping does not replace the output contract;
   - public and hidden fixture IDs, paths, and SHA-256 values map to
     `evaluation.fixtures`, with a source `sha256` or digest represented as the
     fixture `commitment` where the schema requires that name;
   - structured `security`, `privacy`, and `constraints` list items map one-for-one
     to `safety.securityControls`, `safety.privacyControls`, and
     `safety.safetyConstraints` without paraphrase;
   - source-specific tool transports map to the canonical generic kind: command
     interfaces remain `command`, API descriptions map to `api`, and protocol
     surfaces such as MCP or A2A map to `protocol`. Preserve the named transport
     in an evidenced URI only when the source actually provides one; do not
     invent an `interfaceRef`;
   - a single monitoring policy sentence containing several change triggers maps
     as one complete `reassessmentTriggers[].statement`, not one shortened record
     per noun.
   The same source value may support more than one field only when each mapping is
   independently valid. Never use a mapping to erase the original field family.
7. For each reconstructed leaf field, record its value and assessment in the
   adjacent `evidence-map.json` using the contract in
   `references/reconstruction-contract.md`. Use exactly one status:
   `observed`, `declared`, `inferred`, or `unknown`. Classify status from source
   support, not from mapping effort. A directly declared name or tool remains
   `declared`; a directly declared mission or outcome uses claim class
   `evidenced-intended-outcome`, not `inferred-intent`.
   Preserve relational semantics independently from node labels: every trace edge
   source, target, and relation MUST be supported by a declaration or a concrete
   artifact link. Never substitute `decomposedInto`, `implementedBy`, `verifiedBy`,
   or `evidencedBy` for one another merely to make a graph connected. If the
   relationship is ambiguous, omit the edge and record an unknown or omission
   requiring human confirmation.
8. Run `scripts/annotate_reconstruction.py` in a Python environment containing
   pinned `PyYAML==6.0.3` to attach complete field assessments.
   Unassessed fields become `unknown`, confidence `0`, and require confirmation.
   Include override records for schema-required fields deliberately absent from
   the HDP. Those records must have a `null` value, `unknown` status, zero
   confidence, precise missing evidence, and required human confirmation; the
   annotation script retains them in the evidence map even though the JSON
   Pointer does not resolve in the incomplete HDP.
9. Run `scripts/validate_reconstruction.py HDP --inventory source-inventory.json --root HARNESS`
   in an environment containing pinned `PyYAML==6.0.3` and
   `jsonschema[format]==4.25.1`. Fix structure, semantic references, trace/profile
   errors, evidence locations or digests, missing or duplicate field assessments,
   assessment-value mismatches, and confidence/status inconsistencies. Omit
   `--inventory` or `--root` only when that input is genuinely unavailable and
   record the resulting verification limit. An HDP with blocking unknowns MUST
   set `generationReady: false`; do not remove the gate merely to make generation
   pass.
10. Retain `hdp.reconstructed.yaml`, `evidence-map.json`,
   `source-inventory.json`, `coverage-report.json`, `uncertainty-report.json`,
   `codex-binding.yaml`, `HarnessCard.md`, and `parity-suite.json` as one bundle.
   The parity suite MUST compare every directly declared mapped string byte for
   byte after newline normalization, and MUST compare every reconstructed trace
   edge as the ordered tuple `(source, relation, target)` against its cited
   declaration. Treat truncation, added framing text, and relation substitution
   as failures, not acceptable paraphrases. Add a concise review summary covering contradictions, omissions, risks, and
   the smallest human confirmations needed.

## Evidence rules

- `observed`: directly exercised or read back at runtime. Cite command/trace and location.
- `declared`: explicitly stated in an artifact. Cite file plus line, pointer, or key.
- `inferred`: best explanation of multiple artifacts. State alternatives and require confirmation when the field affects outcomes, permissions, safety, or acceptance.
- `unknown`: evidence is absent, inaccessible, contradictory without resolution, or cannot establish intent. State what would resolve it.

Do not report generated tests as an independent acceptance oracle. Do not inspect
hidden fixtures or evaluator secrets from inside the harness boundary. If runtime
observation is not authorized, label behavior as declared or inferred, never observed.
Audit every declared privacy, security, safety, and permission statement. Map it
to the corresponding HDP collection when the schema permits, or retain it as an
explicit omission with its source location and required resolution; an empty
collection must not silently erase a declaration.
Before completion, compare the source privacy, security and safety lists against
`safety.privacyControls`, `safety.securityControls` and
`safety.safetyConstraints`. Duplicating a restriction under prohibited actions
does not satisfy this collection-level coverage check.

## Completion gate

Complete only when:

- the HDP passes structural and semantic validation, or remains an explicitly
  incomplete draft because required intent is genuinely unknown;
- every leaf field has a value and epistemic assessment;
- all evidence locations resolve or are explicitly unavailable;
- contradictions and omissions remain visible;
- blocking unknowns prevent generation;
- intended outcomes are evidence-supported or explicitly unknown;
- declared strings and trace relations pass the lossless parity checks;
- the summary distinguishes conformance evidence from outcome fitness and operational assurance.
