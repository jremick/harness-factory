# Invalidated forward-test runs

The two 2026-08-12 runs in this directory are excluded from every fidelity
result. The skill changed while the agents were running, violating the frozen
input requirement. The foreign run also began while
`references/minimal-reconstruction.yaml` contained a release-notes-specific HDP,
so its source boundary was contaminated by unrelated answer material.

A third run on 2026-08-20 was interrupted before reconstruction when its copied
schema was found to predate the canonical HDP Draft 0.1 schema. It is likewise
excluded; no partial output is scored or reported as evidence.

The generated payloads were moved recoverably to
a local, untracked archive so they cannot
contaminate later runs. Do not restore them into an agent input boundary or use
them as gold data, baselines, or reported test results.
