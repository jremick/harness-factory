# Public alpha verification report

Status: factory software candidate passes; generated harness release blocked
Version: `0.2.0a1`
Date: 2026-08-20

## Decision

The factory is a candidate for an explicitly experimental public alpha. Its
deterministic compiler, generated-harness round trip, isolated wheel consumer,
four managed Codex tasks, policy-block task, tamper detection, and public-surface
checks pass.

The original end-to-end definition of done does **not** fully pass. A fresh
Codex `workspace-write` probe read a canary outside its workspace, so the
workspace-only read boundary and the subject-bound generated-harness release
gate remain failed. Four frozen-input foreign-harness runs also remain retained
failures; the best blind score was `0.947037` with one critical capitalization
mismatch. Under [ADR 0015](decisions/0015-scope-foreign-analysis-as-experimental-in-alpha.md),
the alpha makes no foreign-fidelity claim and the next promotion gate remains
unmet. No failing row is promoted to pass.

The GitHub/Python alpha releases the factory software, not an eligible generated
harness. See [ADR 0014](decisions/0014-separate-factory-alpha-from-harness-release-eligibility.md).

## Evidence ledger

| Gate | Result | Evidence |
| --- | --- | --- |
| Pytest schema, semantic, HIR, installer, packaging and regression suite | pass | 144 tests plus 3 subtests |
| Legacy software-E2E generator suite | pass after manifest repair | 14 unittest cases |
| Deterministic compile, static, analyse, exact diff, ineligible package, verify and tamper path | pass | `evidence/local-verification-current/verification.json` |
| Built-wheel consumer path | pass | `scripts/smoke-consumer.sh` |
| Public repository surface | pass | `tools/check_public_surface.py`, 246 candidate files before the final review/report projection; Gitleaks 8.30.1 found no leaks |
| Live feature task | pass | 82.706 s; Codex 0; evaluator 0; 26 trace events |
| Live defect-fix task | pass | 78.625 s; Codex 0; evaluator 0; 25 trace events |
| Live constrained refactor | pass | 85.077 s; Codex 0; evaluator 0; 25 trace events |
| Live policy-block task | pass | 29.969 s; Codex 0; evaluator 0; 11 trace events |
| One-task no-harness baseline | pass, inconclusive | feature: harness 60.054 s; baseline 64.020 s; both evaluator pass |
| Blind foreign-harness fidelity | fail | best blind run 5: overall 0.947037; 1 false assertion; 1 critical |
| Evaluation-informed foreign regression | fail | overall 0.964835; 1 noncritical false assertion; not a fresh blind claim |
| Network denial probe | pass | direct TCP connect raised `PermissionError` |
| Workspace write/read probe | pass | wrote and read `INSIDE_OK` |
| Outside-workspace read probe | **fail** | canary content was readable under Codex `workspace-write` |
| Subject-bound generated-harness release | **ineligible** | sandbox evidence fails closed |
| Default-branch GitHub CI | pending publication | must be read back after merge |
| Factory release asset install | pending publication | must install from the actual GitHub release URL |

The four-task run used Codex CLI `0.148.0-alpha.15`, requested
`gpt-5.6-sol` with `xhigh`, approval policy `never`, and `workspace-write`.
All evaluator boundaries and randomized canaries remained unchanged, and no run
timed out. The JSONL exposed token counts but no monetary cost or immutable
provider-side model revision.

The one-task baseline is deliberately not an efficacy claim: both variants
passed one feature fixture, and one paired observation is insufficient to show
a quality or efficiency advantage.

## Reproduce

```bash
uv sync --frozen --python 3.12
uv run pytest -q
uv run python -m unittest discover -s workstreams/software-e2e/tests -v
uv run python -m unittest discover -s workstreams/analysis-skill/tests -v
./scripts/smoke-consumer.sh
./scripts/verify-all.sh

uv run python tools/run_local_verification.py \
  --output /tmp/harness-factory-local-verification

uv run python tools/run_reference_e2e.py \
  --codex-binary /path/to/codex \
  --timeout-seconds 600 \
  --output /tmp/harness-factory-reference-e2e

uv run python tools/run_sandbox_probe.py \
  --codex-binary /path/to/codex \
  --output /tmp/harness-factory-sandbox-probe
```

The sandbox command is currently expected to return non-zero on a host where
outside-workspace reads are not denied. That non-zero result is the correct
fail-closed outcome.

## Claim boundaries

- `harness verify` proves deterministic static conformance only.
- Checked-in evaluators are public reproducibility fixtures, not secret
  benchmarks. A new blind claim needs a separately controlled fixture and
  precommitted evaluator.
- Requested model and reasoning settings are recorded; immutable provider-side
  model identity and monetary cost may be unavailable.
- The generated command wrapper is a recorder and precheck, not an OS sandbox.
- `workspace-write` is not represented as workspace-only read isolation.
- Attestations are unsigned, digest-only integrity metadata; they do not
  authenticate a builder or establish a SLSA level or certification.
