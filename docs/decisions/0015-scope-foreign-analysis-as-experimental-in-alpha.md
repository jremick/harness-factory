# ADR 0015: Scope foreign-harness analysis as experimental in the alpha

Status: accepted  
Date: 2026-08-20

## Context

Exact reconstruction of a Harness Factory-generated Codex harness passes
structural, semantic and round-trip parity checks. Six retained attempts against
the same foreign-harness fixture did not meet the precommitted zero-false-
assertion gate. The best fresh blind run scored `0.947037` with one critical
false assertion; an evaluation-informed regression scored `0.964835` with one
noncritical false assertion.

Treating that failed research measure as a passing public-alpha acceptance gate
would be false. Treating it as a mandatory publication gate would also prevent
shipping the deterministic compiler and exact managed-harness analyser, whose
claims are independently testable and useful.

## Decision

- The public alpha claims exact, evidenced reconstruction only for harnesses
  carrying the canonical embedded source definition emitted by this factory.
- Foreign-harness inventory and draft reconstruction are experimental. They
  must remain non-generation-ready when required facts are unknown, exit
  non-zero unless `--allow-partial` is explicit, and must not be described as a
  fidelity-qualified reconstruction.
- Retained foreign runs remain failures in public evidence. A new held-out
  fixture with zero false assertions is the next gate for promoting the foreign
  analyser beyond experimental status; it is not a gate for publishing the
  narrower factory software alpha.
- Generated-harness release eligibility remains independent and fail-closed;
  this decision does not waive sandbox, behaviour, parity or evidence gates.

## Rejected alternatives

- Relabel the best blind run as pass: rejected because it contains a critical
  false assertion.
- Remove the foreign analyser: rejected because an explicitly partial,
  provenance-bearing draft is useful and exposes uncertainty better than a
  plausible complete guess.
- Tune again on the same fixture and call the result blind: rejected because
  repeated exposure invalidates a fresh-blind claim.
