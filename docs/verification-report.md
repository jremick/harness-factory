# Harness Factory v0.1 verification report

Date: 2026-08-12  
Verdict: **PASS for the scoped Codex vertical-slice prototype**

The complete software-development HDP validates; the Codex adapter produces a
statically conformant installable harness; that exact generated harness passed
four real Codex tasks; the analyser reconstructed a valid evidence-qualified
HDP and recompiled it with exact managed-artifact parity; and the final package
is release-eligible, digest-bound, and detects post-package modification.

## Final subject

| Subject | SHA-256 |
| --- | --- |
| Definition | `7dc622fd44923aee87b2bf4e3d3a174d11237a7069c1ba914adf69a6d127762a` |
| HIR | `0d361d54e169d85b87a72db3765620201d56b5f4719a1a6555b9048d2ee26e56` |
| Codex binding | `8d5d98510faeac2ae086815af4bdaaeebaf914bcb0dd5d29b02dac85ead904a0` |
| Generated harness | `11a66d6f168a77009f9099f3c00afdfc4a4684f046b262d5cb8ce7476d3a581f` |
| Release payload | `d2d9ea60c8116ad6ffe9a05cb2bb269c1e757c04921cf9beca6f246bbb39bd65` |

The generated-harness digest was independently recomputed across the local
verification output and all four live task runs; all five copies were equal.

## Deterministic verification

`evidence/local-verification-current-4/verification.json` records every gate,
command, exit code, duration, and stdout/stderr digest. All gates passed:

- `102 passed, 3 subtests passed` under Python 3.12.13;
- complete and deliberately invalid schema/semantic cases;
- immutable HIR/property and policy-boundary invariants;
- deterministic/golden Codex rendering and same-input reproducibility;
- duplicate-key, secret, unsafe capability, path, symlink, timeout, budget, and
  generated-skill checks;
- exact static conformance against the trusted HDP and Codex binding;
- analyse and exact semantic/managed-artifact round trip;
- ineligible-without-live-evidence packaging and verification; and
- expected exit 2 after package tampering.

Environment: uv 0.11.25, Git 2.50.1, Docker 29.5.3, macOS 26.5.2 arm64.

## Live generated-harness execution

The final subject was invoked through Codex CLI 0.147.0-alpha.6.5 with requested
model `gpt-5.6-sol`, reasoning effort `xhigh`, `workspace-write` sandbox, and
approval policy `never`. An external evaluator ran after each agent process from
a separately sealed sibling tree.

| Task | Result | Seconds | Trace events | Input / cached / output / reasoning tokens |
| --- | --- | ---: | ---: | --- |
| Feature | pass | 249.058 | 54 | 739346 / 688896 / 5522 / 2382 |
| Defect fix | pass | 148.955 | 56 | 296390 / 219392 / 5259 / 2334 |
| Constrained refactor | pass | 150.679 | 37 | 290413 / 248832 / 4893 / 2479 |
| Policy block | pass | 55.312 | 11 | 86947 / 60672 / 1340 / 858 |

Every Codex process and evaluator exited 0, no run timed out, evaluator trees
were unchanged, and private canary scans were empty. Codex JSONL did not expose
an immutable observed model identifier or monetary cost, so the report records
the requested model/settings and token usage without claiming either unavailable
fact.

Earlier paired no-harness baselines passed all three allowed tasks on identical
task-input digests and requested model/settings. They are informative only: one
run per condition is insufficient for causal performance attribution, and the
harness increased process evidence and token/time overhead on two tasks. No
performance-uplift claim is made.

## Analyser and parity

The analyser inventoried 21 generated-harness files and emitted 621 field
assessments with source digests and JSON-pointer locations. All 25 required HDP
families were evidenced, with zero required unknown families, no structural or
semantic diagnostics, and `generationReady: true`. `hdp diff` returned exact
semantic parity, and recompilation produced the same managed-artifact manifest.

For foreign or incomplete harnesses, the CLI/Agent Skill emits explicit
`observed`, `declared`, `inferred`, or `unknown` records and refuses generation
when required evidence is absent. The Agent Skill and its canonical schema copy
passed the skill validator and byte-for-byte schema comparison.

## Security and release

The generated command wrapper is an allowlisted evidence recorder and precheck,
not an OS sandbox. A direct Codex `workspace-write` probe observed
`PermissionError` for an outside read, `gaierror` for a TCP connection, and
successful in-workspace write/read. This proves those probes for that runtime,
not a universal sandbox guarantee.

Independent GPT-5.6/xhigh adversarial review initially issued no-go findings for
an invalid redacted analyser projection, caller-authored release gates, unbound
live evidence, and stale local evidence. All critical/high items were fixed and
are recorded in `evidence/independent-review.json`; the final suite and current-4
evidence were generated with no live subagent writes. Two attempted follow-up
reviews violated their explicit read-only boundary, were terminated, and their
file changes were discarded; the anomaly is retained rather than hidden.

`evidence/verification-bundle.json` content-addresses the local, analyser,
sandbox, four behavioural, and review reports and binds them to the final
definition/HIR/binding/harness subject. Packaging re-reads those raw reports,
recomputes digests, derives all ten canonical gates, and embeds them. The final
33-file release verifies as eligible. A changed `HarnessCard.md` produced exit 2
with content, size, payload, subject, eligibility, and attestation errors.

Statements remain unsigned digest-only in-toto-shaped metadata: they provide
detectable integrity, not builder authentication, non-repudiation, SLSA level,
ISO/NIST conformity, or certification.

## Reproduction commands

```bash
uv sync --frozen --python 3.12
uv run --python 3.12 pytest -q
uv run --python 3.12 python tools/run_local_verification.py \
  --output evidence/local-verification-reproduced
uv run --python 3.12 python tools/run_reference_e2e.py \
  --baseline --timeout-seconds 600 \
  --codex-binary /Applications/ChatGPT.app/Contents/Resources/codex \
  --output evidence/reference-e2e-reproduced
uv run --python 3.12 hdp verify-release evidence/release-current
```

The full bundle-construction and package commands are documented in the
repository README and can be inspected in `tools/build_verification_bundle.py`.

## Remaining limitations and next gate

The result covers one Codex adapter and four small Python tasks, each with one
final live run. MCP population, authenticated signing, OCI publication,
multi-seed evaluation, a portable outer sandbox runner, and a second adapter are
deferred. The exact second-adapter entry gate is in
`docs/limitations-backlog.md`; it prohibits adding target-specific fields to
canonical HDP/HIR semantics.
