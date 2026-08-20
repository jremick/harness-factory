# ADR 0012: Score evidence-qualified incomplete reconstructions honestly

Status: accepted for public alpha  
Date: 2026-08-20

## Context

A foreign harness may declare a risk's identity, statement, impact and treatment
while omitting schema-required likelihood and residual values. Requiring a
schema-valid reconstruction in that case creates a perverse gate: the analyser
must either discard supported risk facts or invent the missing values. The first
blind public-alpha candidate exposed this contradiction in the precommitted
fixture rubric.

## Decision

- A generated harness carrying its exact declared HDP must reconstruct as valid
  and round-trip exactly.
- A foreign harness may produce an invalid, non-generation-ready draft when the
  source cannot support a required value.
- Every absent required value must have an evidence-map record with a null value,
  `unknown` status, zero confidence, specific missing evidence and required human
  confirmation.
- The foreign fidelity gate does not require raw JSON Schema validity when its
  gold contract declares honest incompleteness. It still requires content,
  evidence-contract, confidence, coverage, zero false assertions and zero
  critical false assertions.
- The blind fixture gold now asserts all four absent risk companion fields as
  required unknowns. This strengthens epistemic checking while removing the
  contradictory validity requirement.

## Consequences

An incomplete reconstruction cannot compile or become release-ready, but it can
pass fidelity when incompleteness is the correct evidenced result. The scorer
continues to report structural diagnostics. A human must supply authoritative
values before generation.

## Rejected alternatives

- Fill missing risk fields with neutral defaults: rejected as fabricated facts.
- Omit the supported risks entirely: rejected as evidence loss.
- Treat every foreign schema failure as acceptable: rejected; only a fixture
  whose gold contract explicitly expects incompleteness may omit that gate.
