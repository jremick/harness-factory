# Software-development HDP reference: integration brief

## Outcome

This workstream now contains a prototype `hdp/v1` generator and a realistic
software-development fixture. It converts YAML or JSON into a usable,
Codex-oriented repository harness without changing the parent application's
dependencies or files outside this workstream.

Risk tier: **Tier 3**. The artifact generates instructions and executable
controls for a tool-using AI agent. It is a reference implementation, not a
production sandbox.

## What was built

- `hdpgen.py`: stdlib validation/generation with optional pinned PyYAML for
  non-JSON YAML; clear errors for missing fields, unknown fields, unsafe paths,
  contradictory writable/prohibited paths, duplicate IDs, unallowlisted
  executables, missing check references, and blocking open requirements.
- `schema/hdp.schema.json`: a strict external contract for `hdp/v1`.
- Generated project surface: `AGENTS.md`, project Agent Skill, role cards,
  scope/evidence/verification/completion scripts, requirements state, evidence
  ledger, manifest, and requirement-to-artifact source map.
- Stable trace IDs derived from canonical validated input. Fixture trace:
  `HDP-5F37BB1FEA89AAC4`.
- Regeneration safety: manifest hashes protect generated files from silent
  overwrite. Declared manual-extension paths are initialized once and preserved.
- A small unfinished stockroom repository whose `TASK.md` defines product
  behavior while the HDP defines only the operating harness, scope, and proof.
- A sibling `fixture/evaluator/` containing independent tests and a synthetic
  leakage canary. It is not generator input. Its checked-in files have no write
  bits; the clean runner additionally changes the copied evaluator to mode `000`
  for the agent process and restores read-only modes only for evaluation.
- `tools/run_clean_agent.py`: a fresh-workspace `codex exec --ephemeral`
  boundary that preserves the command, prompt, JSONL log, stderr, last message,
  git diff/status, evaluator hashes/results, and machine-readable summary.

## Verification evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| YAML validation | Pass | `python3 hdpgen.py validate fixture/harness.yaml` returned `VALID: HDP-5F37BB1FEA89AAC4`. |
| Generator and deterministic controls | Pass | 14 `unittest` cases passed in 0.533s. |
| Functional generated harness | Pass | A generated smoke repository required ordered process events, ran shell-free checks, and produced a trace-matched completion record. |
| Invalid/contradictory definitions | Pass | Missing field, path contradiction, duplicate check, unknown check, blocking open requirement, and unallowlisted executable all failed loudly. |
| Regression | Pass | All managed fixture artifact hashes matched `tests/golden/fixture-managed-hashes.json`. |
| Prohibited paths | Pass | Parent traversal and symlink escape returned deny; an allowlisted `src` path returned allow. |
| Evaluator boundary | Pass for deterministic boundary checks | Canary absent, sibling hashes unchanged, and seal/restore modes covered by tests. |
| Actual clean Codex execution | Blocked | Codex reached the model but every read-only tool call failed while negotiating with the code-mode host; no repository diff or completion evidence was produced. |

The complete deterministic summary is in
`evidence/verification-summary.json`. Actual-run evidence is retained under:

- `runs/actual-clean-20260812/artifacts/` — default run. `codex.stderr.log`
  records repeated `timed out negotiating with the code-mode host` errors.
- `runs/actual-clean-fallback-20260812/artifacts/` — diagnostic retry proving
  that disabling the host is not a fallback; the CLI explicitly failed closed.

Both runs report `boundary_unchanged: true`, empty workspace diffs, evaluator
failure against the intentionally unimplemented fixture, and no completion
artifact. Codex returning exit code 0 indicates a completed model turn, not a
successful software task; the outer evaluator/completion gates correctly reject
that false-positive condition.

## Security and design findings

- Generated verification uses argv arrays with no shell, allowlisted executable
  basenames, repository-contained working directories, bounded timeouts/output,
  and a minimal environment that omits inherited credentials.
- Scope validation resolves symlinks and fails closed on absolute paths or
  parent traversal. External writes and secret use are definition-level hard
  denials.
- Evaluator files contain no real secret. The canary is synthetic and exists
  solely to detect leakage.
- No new authentication was attempted. Both Codex runs used already-configured
  local auth and `--ignore-user-config`; neither accessed or printed credentials.
- Only one dependency is declared: `PyYAML==6.0.3` for full YAML parsing. JSON
  definitions and all deterministic controls use the standard library.

## Residual risks and open proof

- A successful autonomous Codex implementation remains unverified because the
  local CLI's code-mode host could not execute commands. The fixture evaluator
  is intentionally red until an agent actually implements `TASK.md`.
- The generated `network: deny` policy is enforced by instructions and the
  outer Codex sandbox, not by a portable OS network namespace inside
  `run_verification.py`. A production runner needs a platform-native network
  deny control.
- Path controls enforce writes and the clean runner seals its copied evaluator,
  but this prototype is not a multi-user or hostile-process security sandbox.
- The handwritten validator and published JSON Schema are parallel contracts;
  regression tests reduce but do not eliminate schema/implementation drift.
- Retired generated files are preserved rather than deleted. This is safe for
  data retention but may leave a stale artifact that requires explicit cleanup.

## Recommended action

Integrate this as the software-development reference prototype, with the actual
agent E2E gate marked **blocked**, not passed. After the local code-mode host is
healthy, rerun:

```sh
python3 tools/run_clean_agent.py --output runs/<new-run-id>
```

Accept the autonomous path only when `summary.json` reports all four conditions:
Codex exit 0, generated completion gate true, independent evaluator exit 0, and
unchanged evaluator hashes. Production hardening should next add OS-level
network isolation and a single generated validation contract to remove
schema/validator drift.

