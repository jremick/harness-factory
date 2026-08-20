#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
smoke_root="$(mktemp -d)"
cleanup() {
  case "$smoke_root" in
    /tmp/*|/private/tmp/*|/var/folders/*) rm -rf -- "$smoke_root" ;;
    *) printf 'Refusing to remove unexpected smoke directory: %s\n' "$smoke_root" >&2 ;;
  esac
}
trap cleanup EXIT

distribution_dir="$smoke_root/dist"
environment_dir="$smoke_root/venv"
project_dir="$smoke_root/project"
target_dir="$smoke_root/target"
mkdir -p "$distribution_dir" "$target_dir"

uv build --no-create-gitignore --out-dir "$distribution_dir" "$repository_root"
uv venv --python 3.12 "$environment_dir"
uv pip install --python "$environment_dir/bin/python" "$distribution_dir"/*.whl

"$environment_dir/bin/harness" init "$project_dir" --template codex-sdlc
"$environment_dir/bin/harness" build "$project_dir"
"$environment_dir/bin/harness" install "$target_dir" --project "$project_dir" --dry-run
"$environment_dir/bin/harness" install "$target_dir" --project "$project_dir"
"$environment_dir/bin/harness" verify "$project_dir"

test -f "$target_dir/AGENTS.md"
test -f "$target_dir/.agents/skills/codex-ai-sdlc/SKILL.md"
test -f "$target_dir/.harness-factory/install-manifest.json"

printf 'CONSUMER_SMOKE_PASS wheel install, init, build, dry-run, install, verify\n'
