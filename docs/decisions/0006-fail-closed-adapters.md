# ADR 0006: Fail-closed adapters and multi-view parity

- Status: accepted
- Date: 2026-08-12

## Decision

An adapter reports unsupported material semantics and blocks release. Round-trip
analysis compares semantic, structural, and behavioural views; permissions,
denials, approvals, and security-relevant relations require exact parity.

## Rejected alternatives

Lossy best-effort compilation and one weighted parity score were rejected because
either can hide authority expansion behind an otherwise high score.
