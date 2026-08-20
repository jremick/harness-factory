# ADR 0011: Treat checked-in evaluators as public fixtures

Status: accepted for public alpha

## Context

The repository contains evaluator code, expected results and synthetic canaries
so contributors can reproduce boundary and acceptance tests. Once the repository
is public, those values are visible to people and models with repository access.
Filesystem isolation during a run still protects the evaluator-owned directory,
but it cannot make published content secret or genuinely held out.

## Decision

- Checked-in evaluator packages are public reproducibility fixtures.
- Their synthetic canaries demonstrate boundary enforcement and leakage
  detection; they are not secrecy claims or benchmark holdouts.
- A genuine blind or held-out evaluation must be supplied from an untracked,
  separately permissioned location and its commitment recorded before execution.
- Generated harnesses and model workspaces must still exclude evaluator code,
  expected values and canaries.
- Public reports must use `evaluator-owned` or `public fixture` for checked-in
  material and reserve `private` or `hidden` for separately controlled inputs.

## Consequences

The repository remains reproducible without overstating evaluator independence.
Release evidence must identify whether a gate used a public fixture or a held-out
input. The existing field and file names containing `private` remain compatibility
details until a later schema major version; their publication status is governed
by this decision.

