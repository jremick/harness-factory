# ADR 0007: Deterministic local release and digest-only statements

- Status: accepted
- Date: 2026-08-12

## Decision

The v0.1 release is a deterministic local package with a complete manifest and
in-toto Statement-shaped build/test predicates. Statements are unsigned and
explicitly claim integrity only.

## Rejected alternatives

Immediate OCI publication and unsupported SLSA/authenticity claims were rejected.
OCI/signing remain future extensions after the local verification contract is
proven.
