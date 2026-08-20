# Project contract

## Intent

Build a working factory that compiles a declarative, target-neutral HDP into a
tested target harness, and an evidence-aware analyser that reconstructs existing
harnesses without inventing unknown facts.

## Public-alpha success criteria

- A complete HDP validates and invalid or contradictory definitions fail closed.
- The Codex adapter emits a useful, installable software-development harness.
- Generated harnesses complete the four reference tasks under an outer sandbox.
- Analysis records provenance and uncertainty, exactly round-trips managed
  harnesses, and labels foreign reconstruction experimental until it passes a
  new held-out zero-false-assertion gate.
- Release artifacts bind content digests, source maps, conformance evidence,
  HarnessCard data and tamper-detecting attestations.
- A wheel installed into an isolated environment completes the documented
  `init -> build -> install -> verify` consumer path.

## Risk tier and primary failure modes

Tier 3: reusable AI-agent tooling with autonomous code execution. Primary
failure modes are evaluator leakage, circular self-evaluation, permissive or
underspecified policy projection, destructive installation, fabricated analyser
facts, stale evidence, non-reproducible model execution and evidence not bound to
the released subject.

## Scope

In scope: HDP/HIR contracts, validators, Codex adapter, convention-driven CLI,
managed installation, existing-harness analysis, Agent Skill, fixtures, external
evaluators, tests, evidence, documentation and release packaging.

Out of scope for the alpha: a web UI, Kubernetes or workflow platform, a second
full adapter, multiple synthesis providers, an in-process security sandbox,
authenticated signing, OCI publication and formal standards certification.

## Stop conditions

Stop before weakening an acceptance gate, exposing held-out evaluator material
to the agent, inventing a required analyser value, overwriting an unowned target
file, creating a new authentication route, or claiming a live or released state
without authoritative read-back evidence.
