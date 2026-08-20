# Public alpha verification ledger

Status: factory candidate verified; generated-harness release ineligible

| Criterion | Check | Result | Evidence or gap |
| --- | --- | --- | --- |
| AC1 | Strict/partial analyser CLI tests | pass | exact generated round trip and honest incomplete foreign drafts |
| AC2 | Negative verification and `scripts/verify-all.sh` | pass | broad deterministic gates rerun after fixture-manifest repair |
| AC3 | Simplified CLI and clean consumer | pass | isolated built-wheel smoke |
| AC4 | Managed install safety | pass | manifest ownership, digest, symlink, race and stale-file tests |
| AC5 | Existing regression suites | pass | 136 pytest cases plus 3 subtests; 14 software-E2E tests |
| AC6 | Public-surface audit | pass | local links, private markers and pinned Actions checked |
| AC7 | Default-branch CI | pending | authoritative read-back required after merge |
| AC8a | Four-task live evaluation | pass | feature, defect, refactor and policy-block evaluator passes |
| AC8b | Experimental foreign-harness promotion gate | fail, non-blocking for the narrower alpha under ADR 0015 | best blind score 0.947037; one critical false-assertion category |
| AC8c | Workspace-only sandbox boundary | fail | current `workspace-write` run read an outside canary |
| AC9 | Public-path and secret hygiene scan | pass | 253-file public-surface check; Gitleaks 8.30.1 found no leaks |
| AC10 | GitHub visibility/security/settings | pending | read back after visibility change |
| AC11 | Factory alpha release install | pending | install from the actual GitHub release asset |
| AC12 | Generated-harness release eligibility | fail closed | sandbox evidence prevents an eligible evidence bundle |

## Known residual risks

- Alpha interfaces may change before beta.
- Codex live runs expose requested settings but may not expose immutable model
  identity or monetary cost.
- One passing harness/baseline pair is not efficacy evidence.
- Current Codex `workspace-write` does not satisfy the example's workspace-only
  read contract on this host.
- The foreign analyser has not passed a fresh post-tuning blind fixture.
- Digest-only local attestations prove integrity, not builder identity.
- PyPI publication remains out of scope until a trusted-publisher relationship
  exists.
