# Changelog

This project follows semantic versioning while it is in public alpha.

## 0.2.0a1 - 2026-08-20

- Establish `harness-factory` as the product distribution while preserving the
  advanced `hdp` compatibility interface.
- Add the convention-driven `harness init`, `build`, `install`, `audit`,
  `verify`, `release` and `doctor` workflow.
- Bundle the Codex software-development starter in the wheel and verify it from
  an isolated consumer environment.
- Add managed installation with explicit ownership, conflict and stale-file
  checks, no-follow directory-relative writes, concurrent-install locking, and
  durable rollback recovery.
- Make partial analysis an explicit non-zero outcome unless acknowledged.
- Align the canonical and analysis-skill schemas byte-for-byte with HDP Draft
  0.1 and keep target-specific executable mappings in the Codex binding.
- Clarify public evaluator fixtures versus genuinely held-out evaluation.
- Close release packaging to the exact manifest-owned harness tree and bind raw
  conformance artifacts to the complete definition/HIR/binding/harness subject.
- Reject hostile pre-existing recovery journals and all symlink/non-regular or
  oversized release inputs before bounded, nonblocking, root-anchored no-follow
  reads.
- Scope foreign-harness reconstruction as experimental until a new held-out
  zero-false-assertion gate passes.
- Add Apache-2.0 licensing, public support/security guidance and CI.

## 0.1.0 - 2026-08-12

- Initial HDP/HIR schema, Codex adapter, analyser, behavioural corpus and
  content-bound local release format.
