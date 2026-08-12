# Harness Factory reference prototype

A working Python 3.12 factory for compiling a target-neutral Harness Definition
Package (HDP) into a Codex software-development harness, executing it against an
independent task corpus, reconstructing it through an evidence-aware analyser,
and packaging digest-bound release evidence.

The current verification state is recorded in
[`docs/verification-report.md`](docs/verification-report.md). A successful build
is not automatically release-eligible: all four live Codex behavioural gates
must also pass for the same generated subject.

## Five-minute quickstart

Prerequisites: Python 3.12 and
[`uv`](https://docs.astral.sh/uv/). Codex is needed only for live behavioural
evaluation.

```bash
uv sync --frozen --python 3.12

uv run hdp validate examples/software-development/hdp.yaml

uv run hdp compile examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml \
  --output build/codex-harness

uv run hdp test build/codex-harness \
  --definition examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml

uv run pytest -q
```

The generated directory is a project-scoped Codex harness containing
`AGENTS.md`, `.agents/skills/codex-ai-sdlc/`, `.codex/config.toml`, deterministic
policy/evidence scripts, HIR and source-map metadata, and `HarnessCard.md`.
Copy it into a target repository or inspect the produced files directly.

Run all deterministic compile/analyse/package/tamper gates with retained JSON
and log evidence:

```bash
uv run --python 3.12 python tools/run_local_verification.py \
  --output evidence/local-verification
```

Run the real generated harness on all four reference tasks, plus no-harness
baselines for the three allowed tasks:

```bash
uv run --python 3.12 python tools/run_reference_e2e.py \
  --baseline --timeout-seconds 600 \
  --output evidence/reference-e2e
```

The runner uses `gpt-5.6-sol`, `xhigh`, `workspace-write`, and `never`, preserves
Codex JSONL and token usage, seals the sibling evaluator while the agent runs,
checks canary leakage, and then executes the independent evaluator. If the
shell-resolved `codex` is unhealthy but ChatGPT includes its CLI, pass
`--codex-binary /Applications/ChatGPT.app/Contents/Resources/codex`.

## Analyse and round trip an existing harness

```bash
uv run hdp analyse build/codex-harness --output build/analysis

uv run hdp diff examples/software-development/hdp.yaml \
  build/analysis/hdp.reconstructed.yaml

uv run hdp compile build/analysis/hdp.reconstructed.yaml \
  --binding build/analysis/codex-binding.yaml \
  --output build/round-trip
```

The same workflow is distributed as the repository Agent Skill
[`analyse-existing-harness`](skills/analyse-existing-harness/SKILL.md). Arbitrary
harnesses produce explicit unknowns rather than invented required values; exact
round-trip compilation is allowed only when the evidence supports it.

## Package and verify

Build the subject-bound evidence bundle after local, sandbox, live-task, and
independent-review reports exist:

```bash
uv run --python 3.12 python tools/build_verification_bundle.py \
  --harness evidence/local-verification-current-4/work/generated-harness \
  --definition examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml \
  --evidence-root evidence \
  --local-verification evidence/local-verification-current-4/verification.json \
  --analyser-coverage evidence/local-verification-current-4/work/analysis/coverage-report.json \
  --sandbox-probe evidence/sandbox-probe-summary.json \
  --independent-review evidence/independent-review.json \
  --behaviour feature=evidence/current-reference-feature/aggregate.json \
  --behaviour defect-fix=evidence/current-reference-defect-fix/aggregate.json \
  --behaviour refactor=evidence/current-reference-refactor/aggregate.json \
  --behaviour policy-block=evidence/current-reference-policy-block/aggregate.json \
  --output evidence/verification-bundle.json
```

```bash
uv run hdp package build/codex-harness \
  --definition examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml \
  --conformance evidence/verification-bundle.json \
  --output build/release

uv run hdp verify-release build/release
```

Without a content-addressed verification-evidence bundle, the package remains
intentionally ineligible. `--conformance` accepts that evidence bundle and
derives all gate decisions by re-reading its bound local, analyser, sandbox,
behavioural, and independent-review reports; it does not accept caller-authored
gate statuses. Statements are unsigned, digest-only in-toto-shaped metadata;
they prove detectable integrity, not builder identity, SLSA level, or
certification.

## CLI

The public commands are `init`, `validate`, `compile`, `analyse`, `test`, `diff`,
`package`, and `verify-release`. `generate` and `inspect` remain hidden
compatibility aliases. Run `uv run hdp COMMAND --help` for exact options.

## Design boundaries

- Canonical HDP/HIR semantics are target-neutral. Codex settings live in a
  separate target binding and adapter.
- Models may synthesize only bounded natural-language slots. Deterministic code
  owns validity, hard-policy checks, test outcomes, packaging, and release
  eligibility.
- `scripts/harnessctl.py` is an allowlisted recorder and precheck, not an OS
  sandbox. The binding must explicitly name outer runtime enforcement.
- External evaluator code, private cases, and canaries stay outside the HDP,
  generated harness, model context, and runtime ledger.

Start with the [architecture](docs/architecture.md),
[working specification](docs/specification.md), [research brief](docs/research-brief.md),
[threat model](docs/threat-model.md), [authoring guide](docs/authoring-guide.md),
and [ADRs](docs/decisions/).
