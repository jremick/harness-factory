# ADR 0008: Generated command recorder is not a sandbox

- Status: accepted after adversarial review
- Date: 2026-08-12

## Context

Adversarial probes showed the generated command wrapper could execute an
unallowlisted executable and an interpreter could read an absolute host path.
Argument heuristics cannot enforce process, filesystem, or network isolation.

## Decision

Treat `harnessctl.py` as an evidence recorder and defence-in-depth precheck.
Claims depending on isolation require an outer Codex, container, or OS sandbox
plus independent negative probes and read-back evidence.

## Consequences

The static package may validate without proving sandbox enforcement. Behavioural
release gates remain blocked when the outer runtime is unavailable or unhealthy.
