# HDP software-development reference workstream

This directory is a dependency-light reference implementation of a Harness
Definition Package (HDP) generator for Codex-oriented software work.

The generator reads an `hdp/v1` YAML or JSON definition, validates the narrow
contract in `schema/hdp.schema.json`, and materializes a repository-local
harness. Generated output includes:

- `AGENTS.md` and a project Agent Skill;
- deterministic scope, evidence, verification, and completion scripts;
- role cards, requirements state, trace metadata, a manifest, and a source map;
- manual-extension locations that are initialized once and never overwritten.

The implementation uses the Python standard library for generation and
validation. JSON inputs have no external dependency. YAML input uses
`PyYAML==6.0.3`, pinned in `requirements.txt`.

## Quick start

```sh
python3 hdpgen.py validate fixture/harness.yaml
python3 hdpgen.py generate fixture/harness.yaml fixture/repository
python3 -m unittest discover -s tests -v
```

The fixture deliberately starts with an unfinished task. The generated harness
describes how to work and prove the result; it does not contain the task's
implementation. `fixture/evaluator/` is a sibling boundary owned by the
evaluator, not by the generated harness.

## Regeneration contract

Generated files are tracked by content hash in `.hdp/manifest.json`. On
regeneration, a manually changed generated file causes a loud failure instead
of being overwritten. `AGENTS.local.md` and `.hdp/manual/` are manual extension
locations: the generator creates initial guidance only when absent and never
updates their contents.

## Test and clean-agent entry points

```sh
python3 -m unittest discover -s tests -v
python3 tools/run_clean_agent.py --output runs/actual-clean
```

The clean-agent runner uses an already-installed `codex exec` only. It neither
discovers nor creates authentication. It puts the agent in a fresh workspace,
seals the evaluator sibling against reads and writes for the duration of the
agent process, then restores evaluator read access for independent checks. It
records the command, JSONL log, last message, git diff, evaluator result, and
summary.
