# Getting started

## Install

Harness Factory requires Python 3.12. Install the alpha release with `uv`:

```bash
uv tool install \
  https://github.com/jremick/harness-factory/releases/download/v0.2.0a1/harness_factory-0.2.0a1-py3-none-any.whl
harness doctor
```

For development, clone the repository and run `uv sync --frozen --python 3.12`.

## Create and review a harness project

```bash
harness init my-harness --template codex-sdlc
```

This creates:

```text
my-harness/
├── harness/hdp.yaml
├── harness/bindings/codex.yaml
└── README.md
```

Before building, review at least the intended outcomes, tools, capabilities,
filesystem/network boundaries, approvals, evaluators and ownership in
`harness/hdp.yaml`. Target-specific model and runtime settings stay in the Codex
binding rather than canonical HDP semantics.

## Build and inspect

```bash
harness build my-harness
find my-harness/build/harness -maxdepth 3 -type f | sort
harness verify my-harness
```

`verify` is deterministic static conformance. It does not claim that a live
Codex run occurred; behavioural conformance is a separate repository maintainer
gate.

## Install into a target repository

```bash
harness install /path/to/repository --project my-harness --dry-run
harness install /path/to/repository --project my-harness
```

The installer verifies the generated manifest and file digests, rejects unsafe
paths and symlink destinations, and will not replace an unowned or locally
modified file, even when an unowned file happens to have identical content.
Writes are serialized, no-follow directory-relative, and journalled for
rollback/recovery. It also stops when a newer harness no longer generates a
previously managed file, so removal requires an explicit review rather than
leaving stale instructions silently active. It records ownership in
`.harness-factory/install-manifest.json` inside the target repository.

If an interrupted process leaves `install-transaction.json`, later installs and
dry-runs stop for explicit manual recovery. The installer never replays a
pre-existing journal supplied by the target checkout.

Review generated instructions and commit them through the target repository's
normal change-review process. The outer Codex runtime remains responsible for
actual sandbox enforcement.

## Start from an existing harness

```bash
harness audit /path/to/repository --output analysis
```

Read `analysis/coverage-report.json` and `analysis/uncertainty-report.json` before
using `analysis/hdp.reconstructed.yaml`. Unknown required values intentionally
block generation until resolved from authoritative evidence.
Use `--allow-partial` only when a non-generation-ready experimental foreign
draft is the intended result.
