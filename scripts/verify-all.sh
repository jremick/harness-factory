#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/hdp-verify.XXXXXX")
binding="$repo_dir/examples/software-development/bindings/codex.yaml"
definition="$repo_dir/examples/software-development/hdp.yaml"
harness="$run_dir/generated-harness"
reconstruction="$run_dir/reconstruction"

cd "$repo_dir"

uv sync --frozen --python 3.12
uv run hdp validate examples/minimal/hdp.yaml --json
uv run hdp validate examples/software-development/hdp.yaml --json
uv run pytest -q
uv run python -m unittest discover -s workstreams/software-e2e/tests -v
uv run python -m unittest discover -s workstreams/analysis-skill/tests -v
uv run hdp compile "$definition" --binding "$binding" --output "$harness"
uv run hdp test "$harness" --definition "$definition" --binding "$binding"
uv run hdp analyse "$harness" --output "$reconstruction"
uv run python skills/analyse-existing-harness/scripts/validate_reconstruction.py \
  "$reconstruction/hdp.reconstructed.yaml"
uv build --wheel --sdist --out-dir "$run_dir/dist"

printf '%s\n' "VERIFIED deterministic gates; retained temporary evidence at $run_dir"
