# Invalidated forward-test runs

The two 2026-08-12 runs in this directory are excluded from every fidelity
result. The skill changed while the agents were running, violating the frozen
input requirement. The foreign run also began while
`references/minimal-reconstruction.yaml` contained a release-notes-specific HDP,
so its source boundary was contaminated by unrelated answer material.

The generated payloads were moved recoverably to
`/Users/jarel/.Trash/hdp-analysis-invalidated-20260812/` so they cannot
contaminate later runs. Do not restore them into an agent input boundary or use
them as gold data, baselines, or reported test results.
