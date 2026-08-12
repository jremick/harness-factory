# AI Harness Factory execution plan

Status: active
Date: 2026-08-12
Owner: root integration agent (GPT-5.6, xhigh)
Risk tier: 3 — executable AI-agent tooling and software-supply-chain artifacts

## Intended result

Deliver a Python 3.12 reference implementation that converts a target-neutral
Harness Definition Package (HDP) into a deterministic, tested, packaged, and
attested Codex harness. The same implementation must analyse an existing
harness into an evidence-qualified draft HDP and demonstrate defined
analyse-to-compile round-trip parity without inventing required unknown facts.

## Acceptance contract

The prototype is complete only if all ten user-specified completion gates have
current evidence. In particular, generator tests alone are not sufficient: an
agent must execute the generated harness against the declared release-notes
fixture, the independent evaluator must accept the result, and permission and
evidence controls must be exercised. Repeated executions expose implementation
variance; they do not justify a broader task-distribution claim.

## Workstreams

1. Standards and current formats (parallel, read-only): primary-source research
   on harness research, Codex/Agent Skills/AGENTS.md, MCP/A2A, observability,
   governance, provenance, and supply-chain attestations.
2. Information architecture and compiler (parallel, read-only): HDP package,
   HIR ontology, validators, compiler stages, analyser evidence model, adapter
   contract, source mapping, and round-trip comparison.
3. Verification and adversarial analysis (parallel, read-only): threat model,
   property/invariant tests, behavioural conformance, release gates, analyser
   fidelity, parity metrics, negative cases, and tamper checks.
4. Root integration: requirements, architecture freeze after all three reports,
   repository implementation, evidence capture, target execution, remediation,
   and final verification.

All three delegated workstreams use GPT-5.6 with xhigh reasoning. They do not
write shared files; the root agent owns integration.

## Implementation sequence

1. Inventory the existing `hdp-reference/` subtree and preserve unrelated
   parent-repository changes.
2. Freeze the minimal architecture only after all three workstreams report;
   record material choices and rejected alternatives as ADRs.
3. Establish Python 3.12 and `uv` metadata; implement the 2020-12 schema,
   typed HIR, semantic validators, normalisation, and stable diagnostics.
4. Implement explicit compiler stages: ingest, structural validation, semantic
   validation, normalisation, plan, bounded synthesis records, deterministic
   render, static conformance, sandboxed behaviour, package, and attestation.
5. Implement one complete Codex adapter producing `AGENTS.md`, Agent
   Skills-compatible files, configuration/MCP bindings when declared,
   deterministic controls, eval assets, source maps, and HarnessCard.
6. Implement `init`, `validate`, `compile`, `analyse`, `test`, `diff`, `package`,
   and `verify-release` CLI workflows, documenting any naming aliases.
7. Implement the analyser CLI and generated Agent Skill with file/line evidence,
   observed/declared/inferred/unknown labels, confidence/conflicts, coverage and
   uncertainty reports, draft HDP, HarnessCard, parity suite, and target replay.
8. Build the software-development HDP and isolated reference task corpus.
9. Run unit, property, golden, reproducibility, security, skill, integration,
   analyser, round-trip, tamper, sandbox, and target-runtime checks. Capture
   commands, versions, inputs, exit codes, outputs, traces, model settings, and
   costs when available.
10. Send architecture/security/tests/evidence to the independent verification
    agent, fix critical findings or record a defensible rationale, then run the
    documented clean-checkout verification path.

## Material assumptions and decisions pending research

- The target-neutral HIR will contain no Codex file names or configuration
  keys; those belong only to adapter bindings and render plans.
- Release eligibility, policy decisions, hashes, test outcomes, and parity
  gates are deterministic. Model synthesis is optional, bounded, recorded, and
  never a release authority.
- YAML is an authoring form; canonical JSON is the digest and reproducibility
  form.
- The local `codex` binary and Docker are candidate target/sandbox runtimes.
  Availability does not imply authentication or safe non-interactive execution.
- The existing untracked `hdp-reference/` files are user-owned starting state.
  They will be retained where compatible and changed only inside that subtree.

## Validation and proof targets

- Invalid and contradictory HDPs fail with stable machine-readable diagnostics.
- Equal fully resolved inputs produce byte-identical deterministic artifacts and
  equal digests; nondeterministic run evidence is stored outside that digest set.
- Generated files trace to HDP JSON Pointers or explicit synthesis records.
- Unsafe capabilities, secret-like material, evaluator leakage, path escapes,
  and post-package tampering fail closed.
- Known analyser fixtures meet per-category coverage and exact-fact thresholds;
  required unknowns remain explicit.
- Analyse to compile preserves the declared parity contract for capabilities,
  permissions, lifecycle states, artifacts, and observable task behaviour.
- A real generated Codex harness changes the declared reference repository
  correctly in repeated clean runs; an external oracle grades results
  independently and exercises prohibited-action probes.

## Stop conditions

Stop before changing the parent application, installing into live `~/.codex`,
creating a new credential path, using paid external model calls without an
already authorized route, publishing/deploying, weakening a gate to obtain a
pass, exposing evaluator-private fixtures, or making destructive/irreversible
changes. New evidence that requires a second adapter, web UI, workflow platform,
or external service is backlog unless separately approved.

## Revert boundary

All planned changes are confined to the untracked `hdp-reference/` subtree.
Until the user separately authorizes version-control publication, no commit,
push, deployment, or global skill installation is part of this plan.
