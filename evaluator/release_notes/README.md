# Release-notes evaluator fixture

This checked-in evaluator is a **public reproducibility fixture**. It is kept
outside the generated harness and is made unreadable and unwritable to the agent
during controlled runs. Its expected values and synthetic canary are nevertheless
visible to anyone who can read this repository, so they are not a held-out
benchmark or a secrecy boundary.

The fixture verifies that:

- the generated harness does not copy evaluator-owned material;
- the candidate process cannot read or modify the separately permissioned
  evaluator directory during the run;
- independent deterministic acceptance checks run after the candidate exits;
- evaluator inputs remain unchanged and leakage scans remain empty.

For a genuinely blind evaluation, provide the evaluator package from an
untracked, separately controlled location and record its digest commitment before
execution. See [`docs/evaluator-boundary.md`](../../docs/evaluator-boundary.md)
and [ADR 0011](../../docs/decisions/0011-public-evaluator-fixture-semantics.md).
