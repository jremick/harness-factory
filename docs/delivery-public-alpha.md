# Public alpha delivery brief

## Source of truth

- Product repository: `jremick/harness-factory`, branch `codex/public-alpha`.
- Contract repository: `jremick/hdp-reference`, pinned through the read-only
  `reference` remote.
- Baseline: Harness Factory commit `7a57b02`; HDP Reference commit `d8cb11a`.
- Owner and release approver: Jarel Remick.

## Value hypothesis

Harness authors should be able to generate, install, inspect, verify and release
a Codex harness without learning the compiler's internal file paths or manually
assembling evidence bundles. Public readers should be able to install the tool,
run a real example and understand its assurance limits from a clean checkout.

Measurable outcomes:

- one convention-driven `harness` workflow covers common use;
- the existing `hdp` interface remains compatible;
- partial analyser results cannot be mistaken for valid reconstructions;
- a clean external consumer can build and install a harness;
- both repositories meet the public-alpha gate and read back as public;
- a prerelease is published only from a frozen, verified commit.

## Scope

In scope: fail-closed analysis, simplified CLI, safe managed installation,
public documentation and policies, CI, package metadata, repository security
settings, live behavioural evidence, public visibility and an alpha prerelease.

Non-goals: a second target adapter, a web UI, stable-API claims, automatic PyPI
publication without a configured trusted publisher, or weakening evaluator and
release gates to achieve publication.

Stop conditions:

- a deterministic or behavioural gate fails and cannot be repaired in scope;
- tracked private data, credentials or evaluator-only material is found;
- public visibility would expose a known critical/high security defect;
- package publication requires a new authentication path not already approved.

## Risk classification

Tier 3: this changes a reusable AI-agent toolchain, CI and supply-chain surfaces,
executes external model tasks, and makes repositories public. Required gates are
architecture, security, AI-risk, supply-chain, automated and manual validation,
rollback, independent review, and explicit public-release approval. The user's
instruction to proceed through phases 1-4 supplies that approval subject to the
stop conditions above.

## Architecture and rollback

- `harness` is the product interface; `hdp` remains a compatibility interface.
- Canonical HDP/HIR semantics remain target-neutral and version-pinned.
- The simplified commands orchestrate existing deterministic primitives rather
  than bypassing them.
- Live evaluation remains separately controlled and opt-in.
- Installation writes only manifest-owned files, supports dry-run and refuses
  unsafe overwrite.
- Git commits and GitHub visibility settings provide the rollback boundaries;
  releases remain prereleases and may be withdrawn without claiming stability.

## Acceptance criteria

| ID | Criterion | Verification |
| --- | --- | --- |
| AC1 | Invalid or partial reconstruction exits non-zero unless explicitly allowed | CLI unit and integration tests |
| AC2 | Verification never prints success after a failed analyser or release gate | negative script test and full script run |
| AC3 | `harness init/build/install/audit/verify/release/doctor` provide a convention-driven path | CLI tests and clean consumer run |
| AC4 | Managed installation supports dry-run and refuses unowned overwrite | integration tests |
| AC5 | Existing `hdp` commands remain compatible | regression suite |
| AC6 | License, security, support, contribution, compatibility and changelog surfaces are complete | public-surface audit |
| AC7 | CI runs frozen install, tests, package build and consumer smoke test | GitHub Actions read-back |
| AC8 | Four-task live gate passes; foreign analysis is published only as a retained-failure experimental surface | machine-readable live evidence, retained blind scores and ADR 0015 |
| AC9 | Both repositories pass tracked-path and secret hygiene checks | deterministic scan |
| AC10 | HDP Reference and Harness Factory are public with hardened settings | GitHub API read-back |
| AC11 | Alpha release assets install and reproduce the quickstart | isolated artifact install |
