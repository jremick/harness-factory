---
name: stockroom-task-delivery
description: "Execute and verify stockroom-task tasks under the generated HDP boundary."
---

# stockroom-task delivery

Version: 1.0.0  
Last updated: 2026-08-12  
Trace ID: `HDP-5F37BB1FEA89AAC4`

## Use this skill

Use this skill for the task in `TASK.md`. Read the repository
`AGENTS.md` first; its scope and safety boundaries are authoritative.

## Workflow

1. Read TASK.md and the current implementation before proposing a change. Then record `inspect-task` with the evidence helper.
2. Read the public tests and identify missing edge coverage. Then record `inspect-tests` with the evidence helper.
3. Make the smallest change that satisfies the task, adding focused public tests if useful. Then record `implement` with the evidence helper.
4. Run every definition-owned verification command and review its result. Then record `verify` with the evidence helper.

Before a write, run `python3 scripts/check_path.py --write <path>`. After the
implementation, run `python3 scripts/run_verification.py`, record the final
process step, and run `python3 scripts/check_completion.py`.

Do not use network access, secrets, parent/sibling paths, external writes, or
unlisted executables unless the source HDP is revised and the harness regenerated.
