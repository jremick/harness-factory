# ADR 0004: Deterministic release authority

- Status: accepted
- Date: 2026-08-12

## Decision

Schema validity, hard-policy compliance, test results, digests, parity, and
release eligibility are decided by deterministic code. Models may fill only
declared prose slots through bounded, digest-recorded synthesis requests.

## Rejected alternatives

Model-authored schemas, permissions, gates, or pass/fail judgements were rejected
because they are not reproducible and create circular self-evaluation.
