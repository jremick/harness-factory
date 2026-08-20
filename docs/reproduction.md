# Reproducing Harness Factory results

Run these commands from a clean Harness Factory checkout with Python 3.12 and
the locked `uv` environment. An authenticated Codex runtime is needed only for
live behavioural runs; deterministic checks do not require it.

## 1. Validate and test the implementation

```bash
uv sync --frozen --python 3.12
uv run hdp validate examples/minimal/hdp.yaml --json
uv run hdp validate examples/software-development/hdp.yaml --json
uv run pytest -q
uv run python -m unittest discover -s workstreams/software-e2e/tests -v
uv run python -m unittest discover -s workstreams/analysis-skill/tests -v
```

The negative tests mutate a valid definition and assert stable structural or
semantic failure. Do not treat the YAML files under `examples/invalid/` as
standalone full definitions; they are compact mutation descriptions.

## 2. Compile the harness

Choose a new empty output path for each clean proof run.

```bash
uv run hdp compile examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml \
  --output build/reproduced-harness
uv run hdp test build/reproduced-harness \
  --definition examples/software-development/hdp.yaml \
  --binding examples/software-development/bindings/codex.yaml
```

Compare `.hdp/manifest.json` and `.hdp/source-map.json` with a second fresh
compilation. Equal canonical inputs must produce equal managed-artifact digests.

## 3. Prepare an agent-visible fixture

Keep evaluator files outside the workspace supplied to the agent.

```bash
mkdir -p evidence/runs/reproduction/workspace
cp -R reference/tasks/feature/repository/. evidence/runs/reproduction/workspace/
cp -R build/reproduced-harness/. evidence/runs/reproduction/workspace/
git -C evidence/runs/reproduction/workspace init
git -C evidence/runs/reproduction/workspace add .
git -C evidence/runs/reproduction/workspace \
  -c user.name='HDP Evidence' -c user.email=hdp@example.invalid \
  commit -m 'baseline fixture and generated harness'
```

Invoke a GPT-5.6-sol agent at xhigh reasoning with its working directory set to
the exact workspace. Give it this instruction and no evaluator path:

```text
Operate only inside this workspace. Follow its generated AGENTS.md, Agent Skill,
.codex configuration, runtime policy, TASK.md, and public tests. Do not inspect
any parent or sibling directory. Complete the task, use scripts/harnessctl.py for
required verification evidence, inspect the final diff, and record the required
completion summary.
```

Preserve the agent invocation metadata, exact prompt, transcript/JSONL when the
runtime exposes it, exit status, workspace status, binary diff, evidence ledger,
logs, and run summary. A model label in a binding is a request, not proof of the
observed runtime; preserve provider/runtime readback when available.

## 4. Evaluate from outside the workspace

```bash
uv run python reference/tasks/feature/evaluator/evaluate.py \
  evidence/runs/reproduction/workspace harness
git -C evidence/runs/reproduction/workspace diff --binary \
  > evidence/runs/reproduction/workspace.diff
git -C evidence/runs/reproduction/workspace status --short \
  > evidence/runs/reproduction/workspace-status.txt
```

The evaluator must run as a separately controlled process with no candidate
access to evaluator-private paths. On a platform where that isolation cannot be
enforced, functional results may still be recorded but evaluator-confidentiality
and operational-assurance gates remain inconclusive.

## 5. Reconstruct an HDP

For a generated harness, the embedded declared HDP must reconstruct as valid and
round-trip exactly:

```bash
uv run hdp analyse build/reproduced-harness \
  --output build/reconstructed-generated
uv run python skills/analyse-existing-harness/scripts/validate_reconstruction.py \
  build/reconstructed-generated/hdp.reconstructed.yaml
uv run hdp diff examples/software-development/hdp.yaml \
  build/reconstructed-generated/hdp.reconstructed.yaml
```

For a foreign harness, copy `skills/analyse-existing-harness` and the harness to
a read-only isolated input directory, hash every input before and after, and run
a fresh agent with no access to gold manifests or prior reconstructions. Score
the result afterward with `workstreams/analysis-skill/score_fidelity.py`.

## 6. Interpret results

- A schema/semantic pass establishes definition conformance only.
- A compilation pass establishes deterministic derivation and static checks,
  not outcome fitness.
- An external functional pass supports the declared fixture outcome for the
  exact evaluated subject.
- A command wrapper is a recorder and precheck, not an OS sandbox.
- Unsigned digest-only statements establish internal integrity, not identity or
  non-repudiation.
- Keep `fail`, `blocked`, `not-run`, and `inconclusive` distinct from `pass`.
