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
   pass validation. Add stable IDs and trace links without claiming that an ID
   proves a fact.
6. For each reconstructed leaf field, record its value and assessment in the
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
7. Run `scripts/annotate_reconstruction.py` in a Python environment containing
   pinned `PyYAML==6.0.3` to attach complete field assessments.
   Unassessed fields become `unknown`, confidence `0`, and require confirmation.
8. Run `scripts/validate_reconstruction.py HDP --inventory source-inventory.json --root HARNESS`
   in an environment containing pinned `PyYAML==6.0.3` and
   `jsonschema[format]==4.25.1`. Fix structure, semantic references, trace/profile
   errors, evidence locations or digests, missing or duplicate field assessments,
   assessment-value mismatches, and confidence/status inconsistencies. Omit
   `--inventory` or `--root` only when that input is genuinely unavailable and
   record the resulting verification limit. An HDP with blocking unknowns MUST
   set `generationReady: false`; do not remove the gate merely to make generation
   pass.
9. Retain `hdp.reconstructed.yaml`, `evidence-map.json`,
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
