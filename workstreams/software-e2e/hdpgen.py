#!/usr/bin/env python3
"""Generate a deterministic Codex software-development harness from HDP v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


GENERATOR_NAME = "hdp-software-reference"
GENERATOR_VERSION = "0.1.0"
GENERATOR_DATE = "2026-08-12"
ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
REQ_RE = re.compile(r"^[A-Z][A-Z0-9-]{1,62}$")
EXECUTABLE_RE = re.compile(r"^[A-Za-z0-9._+-]+$")


class HDPError(ValueError):
    """A definition or regeneration error safe to show to an operator."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _mapping(
    value: Any,
    location: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HDPError(f"{location}: expected an object")
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        raise HDPError(f"{location}: missing required field(s): {', '.join(missing)}")
    if extra:
        raise HDPError(f"{location}: unknown field(s): {', '.join(extra)}")
    return value


def _nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HDPError(f"{location}: expected a non-empty string")
    if "\x00" in value or "\r" in value:
        raise HDPError(f"{location}: NUL and carriage-return characters are not allowed")
    return value.strip()


def _string_list(value: Any, location: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise HDPError(f"{location}: expected a {qualifier}array")
    return [_nonempty_string(item, f"{location}/{index}") for index, item in enumerate(value)]


def _unique(values: list[str], location: str) -> None:
    duplicates = sorted({item for item in values if values.count(item) > 1})
    if duplicates:
        raise HDPError(f"{location}: duplicate value(s): {', '.join(duplicates)}")


def _safe_relative(value: Any, location: str, *, allow_dot: bool = False) -> str:
    text = _nonempty_string(value, location)
    if "\\" in text:
        raise HDPError(f"{location}: use POSIX '/' separators")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise HDPError(f"{location}: path must stay inside the repository: {text!r}")
    normalized = path.as_posix()
    if normalized in ("", ".") and not allow_dot:
        raise HDPError(f"{location}: repository-wide path is not allowed")
    return normalized


def _id(value: Any, location: str, pattern: re.Pattern[str] = ID_RE) -> str:
    text = _nonempty_string(value, location)
    if not pattern.fullmatch(text):
        raise HDPError(f"{location}: invalid identifier {text!r}")
    return text


def _overlap(left: str, right: str) -> bool:
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    return left_parts == right_parts[: len(left_parts)] or right_parts == left_parts[: len(right_parts)]


def load_definition(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HDPError(f"cannot read definition {path}: {exc}") from exc
    if len(raw.encode("utf-8")) > 1_048_576:
        raise HDPError("definition exceeds the 1 MiB safety limit")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise HDPError(
                "definition is not JSON and YAML support is unavailable; "
                "install the pinned requirement with: python3 -m pip install -r requirements.txt"
            ) from exc
        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise HDPError(f"invalid YAML: {exc}") from exc

    if not isinstance(parsed, dict):
        raise HDPError("/: definition root must be an object")
    return parsed


def validate_definition(source: dict[str, Any]) -> dict[str, Any]:
    data = _mapping(
        source,
        "/",
        (
            "api_version",
            "kind",
            "metadata",
            "intent",
            "workspace",
            "policy",
            "workflow",
            "verification",
            "assumptions",
            "open_requirements",
        ),
    )
    if data["api_version"] != "hdp/v1":
        raise HDPError("/api_version: only 'hdp/v1' is supported")
    if data["kind"] != "SoftwareHarness":
        raise HDPError("/kind: only 'SoftwareHarness' is supported")

    metadata = _mapping(data["metadata"], "/metadata", ("name", "version", "owners"))
    name = _id(metadata["name"], "/metadata/name", NAME_RE)
    version = _nonempty_string(metadata["version"], "/metadata/version")
    owners = _string_list(metadata["owners"], "/metadata/owners", nonempty=True)
    _unique(owners, "/metadata/owners")

    intent = _mapping(data["intent"], "/intent", ("outcome", "task_file", "non_goals"))
    outcome = _nonempty_string(intent["outcome"], "/intent/outcome")
    task_file = _safe_relative(intent["task_file"], "/intent/task_file")
    non_goals = _string_list(intent["non_goals"], "/intent/non_goals")

    workspace = _mapping(
        data["workspace"],
        "/workspace",
        ("repository_root", "writable_paths", "prohibited_paths", "manual_extension_paths"),
    )
    repository_root = _safe_relative(
        workspace["repository_root"], "/workspace/repository_root", allow_dot=True
    )
    if repository_root != ".":
        raise HDPError("/workspace/repository_root: v1 requires '.'")
    writable_paths = [
        _safe_relative(item, f"/workspace/writable_paths/{index}")
        for index, item in enumerate(_string_list(workspace["writable_paths"], "/workspace/writable_paths", nonempty=True))
    ]
    prohibited_paths = [
        _safe_relative(item, f"/workspace/prohibited_paths/{index}")
        for index, item in enumerate(_string_list(workspace["prohibited_paths"], "/workspace/prohibited_paths"))
    ]
    manual_paths = [
        _safe_relative(item, f"/workspace/manual_extension_paths/{index}")
        for index, item in enumerate(
            _string_list(workspace["manual_extension_paths"], "/workspace/manual_extension_paths")
        )
    ]
    for values, location in (
        (writable_paths, "/workspace/writable_paths"),
        (prohibited_paths, "/workspace/prohibited_paths"),
        (manual_paths, "/workspace/manual_extension_paths"),
    ):
        _unique(values, location)
    for writable in writable_paths:
        for prohibited in prohibited_paths:
            if _overlap(writable, prohibited):
                raise HDPError(
                    "/workspace: contradictory writable/prohibited paths: "
                    f"{writable!r} overlaps {prohibited!r}"
                )
        for reserved in (".hdp", ".agents", "AGENTS.md", "scripts", "evidence"):
            if _overlap(writable, reserved):
                raise HDPError(
                    f"/workspace/writable_paths: {writable!r} overlaps generated path {reserved!r}"
                )
    for manual in manual_paths:
        for reserved in ("AGENTS.md", "scripts", "evidence", ".agents"):
            if _overlap(manual, reserved):
                raise HDPError(
                    f"/workspace/manual_extension_paths: {manual!r} overlaps managed path {reserved!r}"
                )

    policy = _mapping(
        data["policy"],
        "/policy",
        ("network", "external_writes", "secrets", "allowed_executables"),
    )
    if policy["network"] not in ("allow", "deny"):
        raise HDPError("/policy/network: expected 'allow' or 'deny'")
    if policy["external_writes"] != "deny":
        raise HDPError("/policy/external_writes: v1 requires 'deny'")
    if policy["secrets"] != "deny":
        raise HDPError("/policy/secrets: v1 requires 'deny'")
    allowed_executables = _string_list(
        policy["allowed_executables"], "/policy/allowed_executables", nonempty=True
    )
    _unique(allowed_executables, "/policy/allowed_executables")
    for index, executable in enumerate(allowed_executables):
        if not EXECUTABLE_RE.fullmatch(executable):
            raise HDPError(f"/policy/allowed_executables/{index}: use an executable basename")

    workflow = _mapping(data["workflow"], "/workflow", ("required_steps", "roles"))
    raw_steps = workflow["required_steps"]
    if not isinstance(raw_steps, list) or not raw_steps:
        raise HDPError("/workflow/required_steps: expected a non-empty array")
    steps: list[dict[str, str]] = []
    for index, item in enumerate(raw_steps):
        step = _mapping(item, f"/workflow/required_steps/{index}", ("id", "instruction", "evidence"))
        steps.append(
            {
                "id": _id(step["id"], f"/workflow/required_steps/{index}/id"),
                "instruction": _nonempty_string(
                    step["instruction"], f"/workflow/required_steps/{index}/instruction"
                ),
                "evidence": _nonempty_string(
                    step["evidence"], f"/workflow/required_steps/{index}/evidence"
                ),
            }
        )
    _unique([step["id"] for step in steps], "/workflow/required_steps/*/id")

    raw_roles = workflow["roles"]
    if not isinstance(raw_roles, list) or not raw_roles:
        raise HDPError("/workflow/roles: expected a non-empty array")
    roles: list[dict[str, Any]] = []
    for index, item in enumerate(raw_roles):
        role = _mapping(
            item,
            f"/workflow/roles/{index}",
            ("id", "purpose", "allowed_actions", "forbidden_actions"),
        )
        roles.append(
            {
                "id": _id(role["id"], f"/workflow/roles/{index}/id"),
                "purpose": _nonempty_string(role["purpose"], f"/workflow/roles/{index}/purpose"),
                "allowed_actions": _string_list(
                    role["allowed_actions"], f"/workflow/roles/{index}/allowed_actions"
                ),
                "forbidden_actions": _string_list(
                    role["forbidden_actions"], f"/workflow/roles/{index}/forbidden_actions"
                ),
            }
        )
    _unique([role["id"] for role in roles], "/workflow/roles/*/id")

    verification = _mapping(
        data["verification"], "/verification", ("commands", "success_criteria")
    )
    raw_commands = verification["commands"]
    if not isinstance(raw_commands, list) or not raw_commands:
        raise HDPError("/verification/commands: expected a non-empty array")
    commands: list[dict[str, Any]] = []
    for index, item in enumerate(raw_commands):
        command = _mapping(
            item,
            f"/verification/commands/{index}",
            ("id", "argv", "cwd", "timeout_seconds"),
        )
        argv = _string_list(command["argv"], f"/verification/commands/{index}/argv", nonempty=True)
        if argv[0] not in allowed_executables:
            raise HDPError(
                f"/verification/commands/{index}/argv/0: executable {argv[0]!r} is not allowlisted"
            )
        timeout = command["timeout_seconds"]
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 600:
            raise HDPError(
                f"/verification/commands/{index}/timeout_seconds: expected integer from 1 to 600"
            )
        cwd = _safe_relative(
            command["cwd"], f"/verification/commands/{index}/cwd", allow_dot=True
        )
        commands.append(
            {
                "id": _id(command["id"], f"/verification/commands/{index}/id"),
                "argv": argv,
                "cwd": cwd,
                "timeout_seconds": timeout,
            }
        )
    command_ids = [command["id"] for command in commands]
    _unique(command_ids, "/verification/commands/*/id")

    raw_criteria = verification["success_criteria"]
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise HDPError("/verification/success_criteria: expected a non-empty array")
    criteria: list[dict[str, Any]] = []
    for index, item in enumerate(raw_criteria):
        criterion = _mapping(
            item,
            f"/verification/success_criteria/{index}",
            ("id", "statement", "checks"),
        )
        checks = _string_list(
            criterion["checks"], f"/verification/success_criteria/{index}/checks", nonempty=True
        )
        unknown_checks = sorted(set(checks) - set(command_ids))
        if unknown_checks:
            raise HDPError(
                f"/verification/success_criteria/{index}/checks: unknown command id(s): "
                + ", ".join(unknown_checks)
            )
        criteria.append(
            {
                "id": _id(
                    criterion["id"], f"/verification/success_criteria/{index}/id", REQ_RE
                ),
                "statement": _nonempty_string(
                    criterion["statement"], f"/verification/success_criteria/{index}/statement"
                ),
                "checks": checks,
            }
        )
    _unique([criterion["id"] for criterion in criteria], "/verification/success_criteria/*/id")

    assumptions = _string_list(data["assumptions"], "/assumptions")
    raw_open = data["open_requirements"]
    if not isinstance(raw_open, list):
        raise HDPError("/open_requirements: expected an array")
    open_requirements: list[dict[str, Any]] = []
    for index, item in enumerate(raw_open):
        requirement = _mapping(
            item, f"/open_requirements/{index}", ("id", "question", "blocking")
        )
        if not isinstance(requirement["blocking"], bool):
            raise HDPError(f"/open_requirements/{index}/blocking: expected a boolean")
        open_requirements.append(
            {
                "id": _id(requirement["id"], f"/open_requirements/{index}/id", REQ_RE),
                "question": _nonempty_string(
                    requirement["question"], f"/open_requirements/{index}/question"
                ),
                "blocking": requirement["blocking"],
            }
        )
    _unique([item["id"] for item in open_requirements], "/open_requirements/*/id")
    blocking = [item["id"] for item in open_requirements if item["blocking"]]
    if blocking:
        raise HDPError(
            "/open_requirements: generation cannot proceed with blocking requirement(s): "
            + ", ".join(blocking)
        )

    return {
        "api_version": "hdp/v1",
        "kind": "SoftwareHarness",
        "metadata": {"name": name, "version": version, "owners": owners},
        "intent": {"outcome": outcome, "task_file": task_file, "non_goals": non_goals},
        "workspace": {
            "repository_root": repository_root,
            "writable_paths": writable_paths,
            "prohibited_paths": prohibited_paths,
            "manual_extension_paths": manual_paths,
        },
        "policy": {
            "network": policy["network"],
            "external_writes": "deny",
            "secrets": "deny",
            "allowed_executables": allowed_executables,
        },
        "workflow": {"required_steps": steps, "roles": roles},
        "verification": {"commands": commands, "success_criteria": criteria},
        "assumptions": assumptions,
        "open_requirements": open_requirements,
    }


def _bullets(values: list[str], empty: str = "None declared.") -> str:
    return "\n".join(f"- {item}" for item in values) if values else f"- {empty}"


def _render_agents(spec: dict[str, Any], trace_id: str) -> str:
    steps = "\n".join(
        f"{index}. `{step['id']}` — {step['instruction']} Evidence: {step['evidence']}"
        for index, step in enumerate(spec["workflow"]["required_steps"], 1)
    )
    criteria = "\n".join(
        f"- `{item['id']}`: {item['statement']} Checks: {', '.join(item['checks'])}."
        for item in spec["verification"]["success_criteria"]
    )
    commands = "\n".join(
        f"- `{item['id']}`: `{json.dumps(item['argv'], ensure_ascii=False)}` from `{item['cwd']}`."
        for item in spec["verification"]["commands"]
    )
    return f"""<!-- Generated by {GENERATOR_NAME} {GENERATOR_VERSION}; do not edit. -->
# {spec['metadata']['name']} project instructions

Trace ID: `{trace_id}`  
Definition version: `{spec['metadata']['version']}`

## Outcome and source of truth

Outcome: {spec['intent']['outcome']}

Read `{spec['intent']['task_file']}` before changing code. The task file and existing
tests define requested product behavior. This harness defines process, permissions,
and proof; it does not replace the task.

## Hard boundaries

- Work only inside this repository. Do not traverse to, read from, or write to a
  parent or sibling path.
- Candidate writes are limited to: {', '.join(f'`{path}`' for path in spec['workspace']['writable_paths'])}.
- Before each write target, run `python3 scripts/check_path.py --write <path>`.
- Generated/control paths and these declared paths are prohibited: {', '.join(f'`{path}`' for path in spec['workspace']['prohibited_paths']) or 'none declared'}.
- Network is `{spec['policy']['network']}`. External writes and secret access are
  denied. Never inspect environment credentials or copy hidden/evaluation material.
- Run only verification executables allowlisted by the definition: {', '.join(f'`{item}`' for item in spec['policy']['allowed_executables'])}.
- Do not edit `AGENTS.md`, `.agents/`, `.hdp/`, `scripts/`, or `evidence/` directly.
  Trusted generated scripts may update evidence files.

## Required process

{steps}

Record each step once, in order:

```sh
python3 scripts/record_step.py <step-id> --note "non-sensitive summary"
```

Run verification before recording the final verification step:

```sh
python3 scripts/run_verification.py
python3 scripts/record_step.py {spec['workflow']['required_steps'][-1]['id']} --note "verification completed"
python3 scripts/check_completion.py
```

## Acceptance and checks

{criteria}

{commands}

## Assumptions

{_bullets(spec['assumptions'])}

## Open requirements

{_bullets([f"{item['id']}: {item['question']} (blocking={str(item['blocking']).lower()})" for item in spec['open_requirements']])}

If new evidence invalidates an assumption or reveals a blocking requirement, stop
and report it rather than silently widening scope.

## Roles and extensions

Role cards live under `.hdp/roles/`. The project skill is under
`.agents/skills/{spec['metadata']['name']}-delivery/SKILL.md`.

Manual extensions may be placed only in the declared extension locations:
{', '.join(f'`{path}`' for path in spec['workspace']['manual_extension_paths']) or 'none'}.
If `AGENTS.local.md` exists, read it after this file. Manual extensions may add
constraints but cannot weaken these generated boundaries.
"""


def _render_skill(spec: dict[str, Any], trace_id: str) -> str:
    description = (
        f"Execute and verify {spec['metadata']['name']} tasks under the generated HDP boundary."
    )
    steps = "\n".join(
        f"{index}. {step['instruction']} Then record `{step['id']}` with the evidence helper."
        for index, step in enumerate(spec["workflow"]["required_steps"], 1)
    )
    return f"""---
name: {spec['metadata']['name']}-delivery
description: {json.dumps(description, ensure_ascii=False)}
---

# {spec['metadata']['name']} delivery

Version: {spec['metadata']['version']}  
Last updated: {GENERATOR_DATE}  
Trace ID: `{trace_id}`

## Use this skill

Use this skill for the task in `{spec['intent']['task_file']}`. Read the repository
`AGENTS.md` first; its scope and safety boundaries are authoritative.

## Workflow

{steps}

Before a write, run `python3 scripts/check_path.py --write <path>`. After the
implementation, run `python3 scripts/run_verification.py`, record the final
process step, and run `python3 scripts/check_completion.py`.

Do not use network access, credential material, parent/sibling paths, external writes, or
unlisted executables unless the source HDP is revised and the harness regenerated.
"""


def _render_role(role: dict[str, Any], trace_id: str) -> str:
    return f"""<!-- Generated role card; do not edit. -->
# {role['id']}

Trace ID: `{trace_id}`

Purpose: {role['purpose']}

## Allowed actions

{_bullets(role['allowed_actions'])}

## Forbidden actions

{_bullets(role['forbidden_actions'])}
"""


def _render_check_path(spec: dict[str, Any], trace_id: str) -> str:
    allowed = json.dumps(spec["workspace"]["writable_paths"], ensure_ascii=False)
    prohibited = json.dumps(spec["workspace"]["prohibited_paths"], ensure_ascii=False)
    return f'''#!/usr/bin/env python3
"""Fail-closed repository write-scope guard. Trace: {trace_id}."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {allowed}
PROHIBITED = {prohibited}

def contained(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", required=True)
    args = parser.parse_args()
    raw = Path(args.write)
    if raw.is_absolute():
        print("DENY: absolute write paths are forbidden", file=sys.stderr)
        return 3
    candidate = (ROOT / raw).resolve(strict=False)
    if not contained(candidate, ROOT):
        print("DENY: write resolves outside repository root", file=sys.stderr)
        return 3
    for item in PROHIBITED:
        if contained(candidate, (ROOT / item).resolve(strict=False)):
            print(f"DENY: write is inside prohibited path {{item}}", file=sys.stderr)
            return 3
    if not any(contained(candidate, (ROOT / item).resolve(strict=False)) for item in ALLOWED):
        print("DENY: write is outside the allowlisted paths", file=sys.stderr)
        return 3
    print(f"ALLOW: {{candidate.relative_to(ROOT)}}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def _render_record_step(spec: dict[str, Any], trace_id: str) -> str:
    steps_literal = json.dumps([step["id"] for step in spec["workflow"]["required_steps"]])
    return f'''#!/usr/bin/env python3
"""Record required process evidence in strict order. Trace: {trace_id}."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = {json.dumps(trace_id)}
REQUIRED = {steps_literal}
EVENTS = ROOT / "evidence" / "process-events.jsonl"

def read_events():
    if not EVENTS.exists():
        return []
    events = []
    for line_number, line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid process evidence at line {{line_number}}: {{exc}}") from exc
        events.append(event)
    return events

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("step_id", choices=REQUIRED)
    parser.add_argument("--note", default="completed")
    args = parser.parse_args()
    if len(args.note) > 500 or "\\n" in args.note or "\\r" in args.note:
        print("DENY: note must be one line and at most 500 characters", file=sys.stderr)
        return 3
    try:
        existing = read_events()
    except ValueError as exc:
        print(f"FAIL: {{exc}}", file=sys.stderr)
        return 2
    actual = [event.get("step_id") for event in existing if event.get("event") == "step"]
    expected_next = REQUIRED[len(actual)] if len(actual) < len(REQUIRED) else None
    if args.step_id != expected_next:
        print(f"FAIL: next required step is {{expected_next!r}}, not {{args.step_id!r}}", file=sys.stderr)
        return 2
    event = {{"event": "step", "note": args.note, "step_id": args.step_id, "trace_id": TRACE_ID}}
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in existing + [event]]
    fd, temporary = tempfile.mkstemp(prefix=".process-", dir=EVENTS.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\\n".join(lines) + "\\n")
        os.replace(temporary, EVENTS)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"RECORDED: {{args.step_id}}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def _render_verification(spec: dict[str, Any], trace_id: str) -> str:
    commands_string = canonical_json(spec["verification"]["commands"])
    commands_literal = json.dumps(commands_string, ensure_ascii=False)
    return f'''#!/usr/bin/env python3
"""Run definition-owned verification without a shell. Trace: {trace_id}."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = {json.dumps(trace_id)}
COMMANDS = json.loads({commands_literal})
RESULTS = ROOT / "evidence" / "verification-results.json"
OUTPUT_LIMIT = 20000

def contained(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False

def limited(value: str) -> str:
    if len(value) <= OUTPUT_LIMIT:
        return value
    return value[:OUTPUT_LIMIT] + "\\n...[truncated by harness]\\n"

def main() -> int:
    results = []
    clean_env = {{
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }}
    for check in COMMANDS:
        cwd = (ROOT / check["cwd"]).resolve(strict=False)
        if not contained(cwd, ROOT):
            result = {{"id": check["id"], "passed": False, "reason": "cwd escaped repository"}}
            results.append(result)
            continue
        try:
            completed = subprocess.run(
                check["argv"],
                cwd=cwd,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=check["timeout_seconds"],
                check=False,
            )
            result = {{
                "argv": check["argv"],
                "id": check["id"],
                "passed": completed.returncode == 0,
                "returncode": completed.returncode,
                "stderr": limited(completed.stderr),
                "stdout": limited(completed.stdout),
            }}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = {{"id": check["id"], "passed": False, "reason": type(exc).__name__}}
        results.append(result)
        print(f"{{'PASS' if result['passed'] else 'FAIL'}}: {{check['id']}}")

    payload = {{"checks": results, "trace_id": TRACE_ID}}
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".verification-", dir=RESULTS.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\\n")
        os.replace(temporary, RESULTS)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return 0 if all(item["passed"] for item in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
'''


def _render_completion(spec: dict[str, Any], trace_id: str) -> str:
    steps_literal = json.dumps([step["id"] for step in spec["workflow"]["required_steps"]])
    command_ids = json.dumps([item["id"] for item in spec["verification"]["commands"]])
    return f'''#!/usr/bin/env python3
"""Gate completion on required process and verification evidence. Trace: {trace_id}."""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_ID = {json.dumps(trace_id)}
REQUIRED_STEPS = {steps_literal}
REQUIRED_CHECKS = {command_ids}
EVENTS = ROOT / "evidence" / "process-events.jsonl"
RESULTS = ROOT / "evidence" / "verification-results.json"
COMPLETION = ROOT / "evidence" / "completion.json"

def fail(message: str) -> int:
    print(f"INCOMPLETE: {{message}}", file=sys.stderr)
    return 2

def main() -> int:
    if not EVENTS.exists():
        return fail("missing process evidence")
    try:
        events = [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid process evidence: {{exc}}")
    actual_steps = [item.get("step_id") for item in events if item.get("event") == "step"]
    if actual_steps != REQUIRED_STEPS:
        return fail(f"required steps {{REQUIRED_STEPS!r}}; observed {{actual_steps!r}}")
    if any(item.get("trace_id") != TRACE_ID for item in events):
        return fail("process trace mismatch")
    if not RESULTS.exists():
        return fail("missing verification results")
    try:
        verification = json.loads(RESULTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid verification results: {{exc}}")
    if verification.get("trace_id") != TRACE_ID:
        return fail("verification trace mismatch")
    checks = verification.get("checks")
    if not isinstance(checks, list):
        return fail("verification checks are missing")
    actual_checks = [item.get("id") for item in checks]
    if actual_checks != REQUIRED_CHECKS:
        return fail(f"required checks {{REQUIRED_CHECKS!r}}; observed {{actual_checks!r}}")
    failed = [item.get("id") for item in checks if item.get("passed") is not True]
    if failed:
        return fail("failed verification: " + ", ".join(str(item) for item in failed))
    payload = {{"complete": True, "required_checks": REQUIRED_CHECKS, "required_steps": REQUIRED_STEPS, "trace_id": TRACE_ID}}
    COMPLETION.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".completion-", dir=COMPLETION.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\\n")
        os.replace(temporary, COMPLETION)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"COMPLETE: {{TRACE_ID}}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def _render_ledger(spec: dict[str, Any], trace_id: str) -> str:
    rows = "\n".join(
        f"| {item['id']} | {item['statement']} | {', '.join(item['checks'])} | pending | | |"
        for item in spec["verification"]["success_criteria"]
    )
    return f"""<!-- Generated evidence template; script-owned result files sit beside it. -->
# Verification ledger

Trace ID: `{trace_id}`

| Criterion | Expected outcome | Check | Result | Evidence summary | Gap/residual risk |
| --- | --- | --- | --- | --- | --- |
{rows}

Deterministic result files:

- `process-events.jsonl` from `scripts/record_step.py`
- `verification-results.json` from `scripts/run_verification.py`
- `completion.json` from `scripts/check_completion.py`
"""


def build_artifacts(spec: dict[str, Any], trace_id: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    skill_path = f".agents/skills/{spec['metadata']['name']}-delivery/SKILL.md"
    artifacts: dict[str, str] = {
        "AGENTS.md": _render_agents(spec, trace_id),
        skill_path: _render_skill(spec, trace_id),
        "scripts/check_path.py": _render_check_path(spec, trace_id),
        "scripts/record_step.py": _render_record_step(spec, trace_id),
        "scripts/run_verification.py": _render_verification(spec, trace_id),
        "scripts/check_completion.py": _render_completion(spec, trace_id),
        "evidence/verification-ledger.md": _render_ledger(spec, trace_id),
        ".hdp/requirements.json": pretty_json(
            {
                "assumptions": spec["assumptions"],
                "open_requirements": spec["open_requirements"],
                "trace_id": trace_id,
            }
        ),
    }
    source_pointers: dict[str, list[str]] = {
        "AGENTS.md": ["/intent", "/workspace", "/policy", "/workflow", "/verification"],
        skill_path: ["/metadata", "/intent", "/workflow", "/verification"],
        "scripts/check_path.py": ["/workspace/writable_paths", "/workspace/prohibited_paths"],
        "scripts/record_step.py": ["/workflow/required_steps"],
        "scripts/run_verification.py": ["/policy/allowed_executables", "/verification/commands"],
        "scripts/check_completion.py": ["/workflow/required_steps", "/verification/commands"],
        "evidence/verification-ledger.md": ["/verification/success_criteria"],
        ".hdp/requirements.json": ["/assumptions", "/open_requirements"],
    }
    for index, role in enumerate(spec["workflow"]["roles"]):
        path = f".hdp/roles/{role['id']}.md"
        artifacts[path] = _render_role(role, trace_id)
        source_pointers[path] = [f"/workflow/roles/{index}"]

    source_map = {
        "artifacts": source_pointers,
        "requirements": [
            {
                "checks": item["checks"],
                "id": item["id"],
                "source": f"/verification/success_criteria/{index}",
            }
            for index, item in enumerate(spec["verification"]["success_criteria"])
        ],
        "trace_id": trace_id,
    }
    artifacts[".hdp/source-map.json"] = pretty_json(source_map)
    source_pointers[".hdp/source-map.json"] = ["/verification/success_criteria", "/workflow", "/workspace"]
    return artifacts, source_pointers


def _read_prior_manifest(target: Path) -> dict[str, Any] | None:
    path = target / ".hdp" / "manifest.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HDPError(f"cannot trust existing .hdp/manifest.json: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("managed_files"), list):
        raise HDPError("cannot trust existing .hdp/manifest.json: invalid structure")
    return value


def _protect_manual_edits(target: Path, prior: dict[str, Any] | None) -> None:
    if prior is None:
        return
    for item in prior["managed_files"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise HDPError("cannot trust existing manifest: invalid managed_files entry")
        path = target / item["path"]
        if not path.exists():
            continue
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise HDPError(f"cannot inspect existing generated file {item['path']}: {exc}") from exc
        if actual != item["sha256"]:
            raise HDPError(
                f"refusing to overwrite manually changed generated file: {item['path']}; "
                "move the change to a declared manual extension and restore the generated file"
            )


def _atomic_write(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
        if executable:
            path.chmod(path.stat().st_mode | 0o111)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _initialize_extensions(target: Path, spec: dict[str, Any], trace_id: str) -> None:
    for relative in spec["workspace"]["manual_extension_paths"]:
        path = target / relative
        if path.exists():
            continue
        if path.suffix:
            content = (
                f"# Manual extension for {spec['metadata']['name']}\n\n"
                f"Initialized for trace `{trace_id}`. This file is user-owned and is never overwritten.\n"
            )
            _atomic_write(path, content)
        else:
            path.mkdir(parents=True, exist_ok=True)
            readme = path / "README.md"
            if not readme.exists():
                _atomic_write(
                    readme,
                    f"# Manual extensions\n\nUser-owned content for `{spec['metadata']['name']}` belongs here.\n",
                )


def generate(definition_path: Path, target: Path) -> dict[str, Any]:
    spec = validate_definition(load_definition(definition_path))
    digest = sha256_text(canonical_json(spec))
    trace_id = f"HDP-{digest[:16].upper()}"
    target.mkdir(parents=True, exist_ok=True)
    task_path = target / spec["intent"]["task_file"]
    if not task_path.is_file():
        raise HDPError(f"task source does not exist in target repository: {spec['intent']['task_file']}")

    prior = _read_prior_manifest(target)
    _protect_manual_edits(target, prior)
    artifacts, source_pointers = build_artifacts(spec, trace_id)
    managed_files = [
        {
            "path": path,
            "sha256": sha256_text(content),
            "source_pointers": source_pointers[path],
        }
        for path, content in sorted(artifacts.items())
    ]
    manifest = {
        "definition": {"sha256": digest, "source": definition_path.name},
        "extension_paths": spec["workspace"]["manual_extension_paths"],
        "format_version": 1,
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
        "managed_files": managed_files,
        "policy_summary": {
            "external_writes": "deny",
            "network": spec["policy"]["network"],
            "parent_and_sibling_access": "deny",
            "secrets": "deny",
        },
        "trace_id": trace_id,
    }

    for path, content in sorted(artifacts.items()):
        _atomic_write(target / path, content, executable=path.startswith("scripts/") and path.endswith(".py"))
    _atomic_write(target / ".hdp" / "manifest.json", pretty_json(manifest))
    _initialize_extensions(target, spec, trace_id)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate without writing")
    validate_parser.add_argument("definition", type=Path)
    generate_parser = subparsers.add_parser("generate", help="validate and generate into a repository")
    generate_parser.add_argument("definition", type=Path)
    generate_parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            spec = validate_definition(load_definition(args.definition))
            digest = sha256_text(canonical_json(spec))
            print(f"VALID: HDP-{digest[:16].upper()}")
            return 0
        manifest = generate(args.definition, args.target)
        print(f"GENERATED: {manifest['trace_id']} -> {args.target}")
        return 0
    except HDPError as exc:
        print(f"HDP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
