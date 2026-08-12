# Project contract

## Intent

Create a working, reproducible specification and reference implementation that
lets an agent generate a fit-for-purpose harness from an explicit definition and
lets a separate evaluator determine whether the resulting model-harness-runtime-
environment system achieved the stated outcomes.

## Good means

All ten completion gates in the user brief pass without evaluator leakage,
unreported failures, or an unverifiable model-execution claim. Another competent
agent can reproduce the result using only this subtree and its documented tools.

## Evidence

- Draft 2020-12 meta-schema and instance validation logs.
- Deterministic semantic-rule failure cases.
- Reproducible generator manifests and golden hashes.
- Captured agent commands, stdout/stderr, exit codes, diffs, and traces.
- Acceptance-oracle output from the external evaluator boundary.
- Permission denial and prohibited-path tests.
- Reconstruction coverage and fidelity reports for two harness structures.

## Risk tier and primary failure modes

Tier 3: this creates reusable AI-agent tooling with autonomous code execution.

Primary failure modes are evaluator leakage, circular self-evaluation, a schema
that permits underspecified harnesses, generated tests that merely validate their
own implementation, destructive regeneration, inferred business outcomes stated
as facts, non-reproducible model execution, and evidence that cannot be traced to
requirements.

## Scope and non-goals

In scope: specification, schemas, validator, generator, examples, isolated
fixture, external evaluator, portable analysis skill, tests, evidence, reports,
and decision records.

Out of scope: deploying or publishing the project, changing the parent CasePilot
application, installing the skill into `~/.codex`, committing or pushing, live
external integrations, secrets, and claims of formal standards conformance not
supported by those standards.

## Stop conditions

Stop before adding an authentication route, using a paid model/API path not
already available, mutating outside `hdp-reference/`, weakening acceptance
criteria, exposing evaluator-private fixtures to the generated harness, or
publishing/deploying artefacts.

