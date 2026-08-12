# ADR 0005: Evidence propositions before reconstructed facts

- Status: accepted
- Date: 2026-08-12

## Decision

The analyser emits observed, declared, inferred, or unknown propositions with
confidence, precise provenance, missing evidence, and conflict sets before
constructing a draft HDP. Required unknowns are never plausibly defaulted.

## Rejected alternatives

Eager best-guess reconstruction and global source precedence were rejected.
Authority is field-specific, and a structurally invalid honest draft is safer
than a valid fabricated one.
