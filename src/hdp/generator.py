"""Deterministic generator for the Codex software-development HDP profile."""

import hashlib
import json
import os
import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from . import __version__
from .diagnostics import HdpGenerationError
from .io import atomic_write_text, canonical_json, dump_json, load_document
from .schema_validation import structural_diagnostics


MANIFEST_PATH = Path(".hdp/manifest.json")
GENERATED_MARKER = "Generated from an HDP. Do not edit; use manual/ for extensions."
_SHA256 = re.compile(r"[0-9a-f]{64}")
_OVERLAY_KEYS = {
    "allowedExecutables",
    "commandBindings",
    "enforcementBoundary",
    "externallyEnforcedResources",
}
_WRAPPER_ENFORCED_HARD_BUDGETS = {"tool-calls"}
_REQUIRED_EXTERNAL_CONTROLS = {"environment", "filesystem", "network", "process"}
_SUPPORTED_EXTERNAL_CONTROLS = _REQUIRED_EXTERNAL_CONTROLS | {"wall-time"}


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_text(content: str) -> str:
    return _sha256_bytes(content.encode("utf-8"))


def _safe_relative_path(value: str, *, label: str) -> str:
    """Return a normalized project-relative POSIX path or fail closed."""

    if not isinstance(value, str) or not value:
        raise HdpGenerationError(f"unsafe {label}: {value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() in {"", "."}:
        raise HdpGenerationError(f"unsafe {label}: {value!r}")
    normalized = pure.as_posix()
    if normalized != value or "\\" in value:
        raise HdpGenerationError(f"unsafe {label}: {value!r}")
    return normalized


def _output_tree_violations(root: Path) -> List[str]:
    """Report symlinks and special files without following either."""

    if not root.exists():
        return []
    violations: List[str] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise HdpGenerationError(f"cannot inspect output tree {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if entry.is_symlink():
                violations.append(f"symlink:{relative}")
            elif entry.is_dir(follow_symlinks=False):
                stack.append(path)
            elif not entry.is_file(follow_symlinks=False):
                violations.append(f"special:{relative}")
    return sorted(violations)


def _prepare_output_root(output: Path) -> Path:
    """Resolve the output root only after rejecting an existing link target."""

    lexical = output.expanduser().absolute()
    if lexical.is_symlink():
        raise HdpGenerationError(f"unsafe output path is a symlink: {lexical}")
    resolved = lexical.resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        raise HdpGenerationError(f"unsafe output path: {resolved}")
    violations = _output_tree_violations(resolved)
    if violations:
        raise HdpGenerationError(
            "output tree contains prohibited symlink or special file: "
            + ", ".join(violations)
        )
    return resolved


def _inside_output(output: Path, relative: str) -> Path:
    normalized = _safe_relative_path(relative, label="generated path")
    candidate = (output / normalized).resolve(strict=False)
    if candidate != output and output not in candidate.parents:
        raise HdpGenerationError(f"generated path escapes output root: {relative!r}")
    return candidate


def _is_manual_extension(relative: str) -> bool:
    return relative == "manual" or relative.startswith("manual/")


def _safe_skill_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not name:
        raise HdpGenerationError("runtime profile id cannot form an Agent Skill name")
    return name[:63].rstrip("-")


def _bullets(values: Iterable[str], *, empty: str = "- None declared.") -> str:
    items = [f"- {value}" for value in values]
    return "\n".join(items) if items else empty


def _statement(record: Mapping[str, Any]) -> str:
    identifier = record.get("id", "UNIDENTIFIED")
    text = record.get("statement") or record.get("description") or "No statement supplied."
    return f"[{identifier}] {text}"


def _agent_instructions(definition: Mapping[str, Any]) -> str:
    metadata = definition["metadata"]
    purpose = definition["purpose"]
    requirements = definition["requirements"]
    governance = definition["governance"]
    permissions = governance["permissions"]
    resources = definition["resources"]
    failures = definition["failures"]
    evaluation = definition["evaluation"]

    outcomes = [_statement(item) for item in purpose["intendedOutcomes"]]
    required = [_statement(item) for item in requirements if item.get("priority") == "must"]
    prohibited = [item["action"] for item in permissions.get("prohibitedActions", [])]
    stops = [_statement(item) for item in resources.get("stoppingConditions", [])]
    recovery = [_statement(item) for item in failures.get("recoveryPolicies", [])]
    public_checks = [
        _statement(item)
        for item in evaluation.get("tests", [])
        if item.get("visibility", "public") == "public"
    ]

    return f"""# Generated harness instructions

<!-- {GENERATED_MARKER} -->

Source HDP: `{metadata['id']}` version `{metadata['version']}`.

## Mission

{purpose['summary']}

The concrete repository task is supplied by the fixture environment. Follow it
without assuming implementation details that are absent from the task or source.

## Intended outcomes

{_bullets(outcomes)}

## Mandatory requirements

{_bullets(required)}

## Operating loop

1. Read the task, repository instructions, directly affected code, and tests.
2. Record assumptions; stop on unresolved requirements that materially change behavior.
3. Make the smallest traceable change inside the allowed workspace.
4. Run required checks through `python scripts/harnessctl.py run` so evidence is captured.
5. Inspect the diff and record a run summary before reporting completion.

If the task requires a prohibited capability, do not implement a substitute.
Record the exact policy decision and stop:

```bash
python scripts/harnessctl.py block --policy POLICY-ID --reason "why the task is prohibited"
```

## Permissions

- Default policy: `{permissions['default']}`.
- Writable paths: {', '.join(permissions.get('filesystem', {}).get('write', [])) or 'none'}.
- Network: `{'allowed' if permissions.get('network', {}).get('allowed') else 'denied'}`.
- Never inspect or modify evaluator-owned paths or private fixtures.
- Treat `harnessctl.py` as a recorder and precheck, not a sandbox. The outer
  Codex/OS runtime is the enforcement boundary.

Prohibited actions:

{_bullets(prohibited)}

## Public verification contract

{_bullets(public_checks)}

Generated/self-authored checks are verification evidence only. They are not the
external acceptance oracle.

## Recovery and stopping

Recovery policies:

{_bullets(recovery)}

Stop conditions:

{_bullets(stops)}

## Evidence

Use:

```bash
python scripts/harnessctl.py run --requirement REQ-ID -- <command> [args...]
python scripts/harnessctl.py summary --status complete
```

Do not claim a check ran unless its command record exists in `evidence/ledger.jsonl`.
"""


def _skill(definition: Mapping[str, Any], skill_name: str) -> str:
    purpose = definition["purpose"]["summary"].strip().replace("\n", " ")
    return f"""---
name: {skill_name}
description: Execute software-development tasks under the generated HDP controls, traceability, permissions, verification loop, and evidence protocol. Use when operating in the repository containing this generated harness.
---

# Execute the HDP software-development harness

Read the repository `AGENTS.md`, `.hdp/runtime-policy.json`, and the concrete task.
Use the declared roles and stages; do not infer absent business outcomes.

Mission: {purpose}

Run required commands through `scripts/harnessctl.py`. Keep evaluator-owned files
outside the working context. Treat generated tests as internal verification and the
external evaluator as the only acceptance oracle. Stop when a declared condition is
met, a prohibited capability is required, or an ambiguity changes observable behavior.
"""


def _role_files(definition: Mapping[str, Any]) -> Dict[str, str]:
    rendered: Dict[str, str] = {}
    for role in definition["orchestration"].get("roles", []):
        responsibilities = role.get("responsibilities", [])
        prohibited = role.get("prohibitedActions", [])
        content = f"""# {role['name']}

<!-- {GENERATED_MARKER} -->

Role ID: `{role['id']}`

## Responsibilities

{_bullets(responsibilities)}

## Prohibited actions

{_bullets(prohibited)}
"""
        rendered[f"roles/{_safe_skill_name(role['id'])}.md"] = content
    return rendered


def _harnessctl_script() -> str:
    return '''#!/usr/bin/env python3
"""Generated command gate and evidence recorder."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / ".hdp" / "runtime-policy.json"
LEDGER = ROOT / "evidence" / "ledger.jsonl"
LOG_DIR = ROOT / "evidence" / "logs"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def inside(path, roots):
    resolved = path.resolve()
    return any(resolved == root or root in resolved.parents for root in roots)


def referenced_paths(arguments):
    for argument in arguments[1:]:
        if not argument or argument.startswith("-"):
            continue
        candidate = Path(argument)
        if candidate.is_absolute() or ".." in candidate.parts:
            yield candidate if candidate.is_absolute() else ROOT / candidate


def run_command(arguments, requirement_ids):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if not arguments:
        raise SystemExit("no command supplied after --")
    unsupported_controls = policy.get("unsupportedEnforcementResources", [])
    if unsupported_controls:
        print(
            "DENIED controls lack an external enforcement binding: "
            + ", ".join(sorted(unsupported_controls)),
            file=sys.stderr,
        )
        return 78
    executable = Path(arguments[0]).name
    allowed_executables = set(policy.get("allowedExecutables", []))
    if executable not in allowed_executables:
        print(f"DENIED executable is not allowlisted: {executable}", file=sys.stderr)
        return 77
    command_text = " ".join(arguments).lower()
    for action in policy.get("prohibitedActions", []):
        if action.lower() in command_text:
            print(f"DENIED prohibited action: {action}", file=sys.stderr)
            return 77
    if not policy.get("network", {}).get("allowed", False):
        network_commands = {"curl", "wget", "ssh", "scp", "nc", "ncat"}
        if Path(arguments[0]).name.lower() in network_commands:
            print("DENIED network command", file=sys.stderr)
            return 77
        if Path(arguments[0]).name.lower() == "git" and len(arguments) > 1 and arguments[1] in {"push", "fetch", "pull", "clone"}:
            print("DENIED network-capable git command", file=sys.stderr)
            return 77
    allowed = [ROOT / item for item in policy.get("filesystem", {}).get("read", [])]
    allowed.extend(ROOT / item for item in policy.get("filesystem", {}).get("write", []))
    for path in referenced_paths(arguments):
        if not inside(path, [item.resolve() for item in allowed]):
            print(f"DENIED path outside allowlist: {path}", file=sys.stderr)
            return 77

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    sequence = sum(1 for _ in LEDGER.open("r", encoding="utf-8")) + 1 if LEDGER.exists() else 1
    tool_limits = [
        int(item["limit"]) for item in policy.get("budgets", [])
        if item.get("resource") == "tool-calls" and item.get("hard")
    ]
    if tool_limits and sequence > min(tool_limits):
        print("DENIED hard tool-call budget exhausted", file=sys.stderr)
        return 78
    command_timeouts = [
        int(item["seconds"]) for item in policy.get("timeouts", [])
        if item.get("onExpiry") == "stop"
    ]
    timeout_seconds = min(command_timeouts) if command_timeouts else 120
    minimal_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    timed_out = False
    try:
        result = subprocess.run(
            arguments, cwd=ROOT, capture_output=True, check=False,
            timeout=timeout_seconds, env=minimal_env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        if isinstance(stdout, str):
            stdout = stdout.encode()
        if isinstance(stderr, str):
            stderr = stderr.encode()
        result = subprocess.CompletedProcess(arguments, 124, stdout, stderr)
        timed_out = True
    prefix = f"{sequence:04d}"
    stdout_path = LOG_DIR / f"{prefix}.stdout.log"
    stderr_path = LOG_DIR / f"{prefix}.stderr.log"
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    record = {
        "event": "command.completed",
        "sequence": sequence,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": arguments,
        "cwd": ".",
        "requirementIds": sorted(set(requirement_ids)),
        "exitCode": result.returncode,
        "timedOut": timed_out,
        "timeoutSeconds": timeout_seconds,
        "enforcementBoundary": policy.get("enforcementBoundary"),
        "stdout": {"path": str(stdout_path.relative_to(ROOT)), "sha256": digest(result.stdout)},
        "stderr": {"path": str(stderr_path.relative_to(ROOT)), "sha256": digest(result.stderr)},
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\\n")
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    return result.returncode


def write_summary(status):
    summary = {
        "status": status,
        "ledger": "evidence/ledger.jsonl",
        "ledgerSha256": digest(LEDGER.read_bytes()) if LEDGER.exists() else None,
    }
    (ROOT / "evidence" / "run-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
    )
    return 0


def write_block(policy_id, reason):
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    known = {item.get("id") for item in policy.get("prohibitedActionRecords", [])}
    if policy_id not in known:
        print(f"unknown prohibited policy id: {policy_id}", file=sys.stderr)
        return 2
    payload = {
        "blocked": True,
        "policyId": policy_id,
        "reason": reason,
        "enforcementBoundary": policy.get("enforcementBoundary"),
    }
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence" / "policy-block.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
    )
    return write_summary("blocked")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--requirement", action="append", default=[])
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    summary = commands.add_parser("summary")
    summary.add_argument("--status", choices=["complete", "incomplete", "blocked"], required=True)
    block = commands.add_parser("block")
    block.add_argument("--policy", required=True)
    block.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "run":
        arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
        return run_command(arguments, args.requirement)
    if args.command == "block":
        return write_block(args.policy, args.reason)
    return write_summary(args.status)


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _state_template(definition: Mapping[str, Any]) -> str:
    stages = [f"[{item['id']}] {item['name']}" for item in definition["orchestration"].get("stages", [])]
    return f"""# Harness state

<!-- {GENERATED_MARKER} -->

## Current stage

Not started.

## Declared stages

{_bullets(stages)}

## Assumptions made during execution

- None yet.

## Open requirements

- None yet.

## Next safe action

Read the concrete task and repository state.
"""


def _assumptions(definition: Mapping[str, Any]) -> str:
    context = definition["operationalContext"]
    assumptions = [_statement(item) for item in context.get("assumptions", [])]
    unresolved = [
        _statement(item)
        for item in definition["requirements"]
        if item.get("status") in {"proposed", "unresolved"}
    ]
    return f"""# Declared assumptions and unresolved requirements

<!-- {GENERATED_MARKER} -->

## Assumptions

{_bullets(assumptions)}

## Unresolved requirements

{_bullets(unresolved)}
"""


def _public_evaluation_contract(definition: Mapping[str, Any]) -> Dict[str, Any]:
    evaluation = definition["evaluation"]
    return {
        "boundary": evaluation["boundary"],
        "metrics": evaluation.get("metrics", []),
        "tests": [
            item for item in evaluation.get("tests", []) if item.get("visibility", "public") == "public"
        ],
        "acceptanceCriteria": definition["success"].get("acceptanceCriteria", []),
    }


def _source_map(definition: Mapping[str, Any]) -> Dict[str, List[str]]:
    role_paths = [
        f"roles/{_safe_skill_name(item['id'])}.md"
        for item in definition["orchestration"].get("roles", [])
    ]
    return {
        "AGENTS.md": [
            "/metadata",
            "/purpose",
            "/requirements",
            "/governance/permissions",
            "/resources/stoppingConditions",
            "/failures/recoveryPolicies",
            "/evaluation/tests",
        ],
        ".agents/skills": ["/purpose", "/runtime/profile", "/governance/permissions"],
        ".hdp/runtime-policy.json": ["/governance/permissions", "/resources"],
        ".hdp/traceability.json": ["/traceability"],
        ".hdp/public-evaluation-contract.json": ["/evaluation", "/success/acceptanceCriteria"],
        ".hdp/source-definition.public.json": [""],
        ".hdp/assumptions.md": ["/operationalContext/assumptions", "/requirements"],
        "STATE.md": ["/orchestration/stages"],
        "scripts/harnessctl.py": ["/governance/permissions", "/observability", "/traceability"],
        **{path: [f"/orchestration/roles/{index}"] for index, path in enumerate(role_paths)},
    }


def _render_files(
    definition: Mapping[str, Any],
    runtime_policy_overlay: Mapping[str, Any] | None = None,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    profile = definition["runtime"]["profile"]
    skill_name = _safe_skill_name(profile["id"])
    permissions = definition["governance"]["permissions"]
    overlay = dict(runtime_policy_overlay or {})
    unknown_overlay_keys = sorted(set(overlay) - _OVERLAY_KEYS)
    if unknown_overlay_keys:
        raise HdpGenerationError(
            "runtime policy overlay cannot replace canonical authority fields: "
            + ", ".join(unknown_overlay_keys)
        )
    external_values = overlay.get("externallyEnforcedResources", [])
    if not isinstance(external_values, list) or not all(
        isinstance(item, str) for item in external_values
    ) or len(external_values) != len(set(external_values)):
        raise HdpGenerationError(
            "externally enforced resources must be a unique list of names"
        )
    externally_enforced = set(external_values)
    unsupported_external_declarations = sorted(
        externally_enforced - _SUPPORTED_EXTERNAL_CONTROLS
    )
    if unsupported_external_declarations:
        raise HdpGenerationError(
            "unsupported external enforcement declaration: "
            + ", ".join(unsupported_external_declarations)
        )
    if "commandBindings" in overlay or "allowedExecutables" in overlay:
        if "commandBindings" not in overlay or "allowedExecutables" not in overlay:
            raise HdpGenerationError(
                "runtime command bindings and allowed executables must be supplied together"
            )
        allowed_ids = set(permissions.get("tools", {}).get("allowedIds", []))
        allowed_commands = {
            item["id"] for item in definition.get("tools", {}).get("interfaces", [])
            if item.get("kind") == "command" and item.get("id") in allowed_ids
        }
        command_bindings = overlay["commandBindings"]
        if not isinstance(command_bindings, Mapping) or set(command_bindings) != allowed_commands:
            raise HdpGenerationError(
                "runtime command bindings must exactly cover governance-allowed command "
                f"capabilities: expected={sorted(allowed_commands)}"
            )
        executable_pattern = re.compile(r"[A-Za-z0-9._+-]+")
        if any(
            not isinstance(values, list)
            or not values
            or len(values) != len(set(values))
            or any(
                not isinstance(executable, str)
                or not executable_pattern.fullmatch(executable)
                for executable in values
            )
            for values in command_bindings.values()
        ):
            raise HdpGenerationError(
                "runtime command bindings must contain unique executable basenames"
            )
        allowed_executables = overlay["allowedExecutables"]
        if (
            not isinstance(allowed_executables, list)
            or not all(isinstance(item, str) for item in allowed_executables)
            or len(allowed_executables) != len(set(allowed_executables))
        ):
            raise HdpGenerationError("allowed executables must be a unique list")
        bound_executables = {
            executable
            for values in command_bindings.values()
            for executable in values
        }
        if set(allowed_executables) != bound_executables:
            raise HdpGenerationError(
                "allowed executables must exactly equal the command-binding projection"
            )
    hard_resources = {
        item["resource"]
        for item in definition["resources"].get("budgets", [])
        if item.get("hard")
    }
    unsupported_hard_budgets = sorted(
        hard_resources - _WRAPPER_ENFORCED_HARD_BUDGETS - externally_enforced
    )
    required_external_controls = (
        _REQUIRED_EXTERNAL_CONTROLS
        | (hard_resources - _WRAPPER_ENFORCED_HARD_BUDGETS)
    )
    unsupported_enforcement = sorted(required_external_controls - externally_enforced)
    runtime_policy = {
        "policyVersion": definition["hdpVersion"],
        "default": permissions["default"],
        "filesystem": permissions.get("filesystem", {}),
        "network": permissions.get("network", {"allowed": False}),
        "tools": permissions.get("tools", {}),
        "prohibitedActions": [
            item["action"] for item in permissions.get("prohibitedActions", [])
        ],
        "prohibitedActionRecords": permissions.get("prohibitedActions", []),
        "approvals": definition["governance"].get("approvals", []),
        "budgets": definition["resources"].get("budgets", []),
        "timeouts": definition["resources"].get("timeouts", []),
        "externallyEnforcedResources": sorted(externally_enforced),
        "requiredExternalEnforcementResources": sorted(required_external_controls),
        "unsupportedEnforcementResources": unsupported_enforcement,
        "unsupportedHardBudgets": unsupported_hard_budgets,
        "enforcementBoundary": (
            "evidence recorder and defence-in-depth precheck only; not an OS sandbox"
        ),
    }
    runtime_policy.update(overlay)
    files: Dict[str, str] = {
        "AGENTS.md": _agent_instructions(definition),
        f".agents/skills/{skill_name}/SKILL.md": _skill(definition, skill_name),
        f".agents/skills/{skill_name}/agents/openai.yaml": (
            'interface:\n'
            f'  display_name: "{definition["metadata"]["title"].replace(chr(34), chr(39))[:64]}"\n'
            '  short_description: "Run controlled software tasks with evidence"\n'
            f'  default_prompt: "Use ${skill_name} to execute this repository task under its generated controls."\n'
        ),
        ".hdp/runtime-policy.json": dump_json(runtime_policy),
        ".hdp/traceability.json": dump_json(definition["traceability"]),
        ".hdp/public-evaluation-contract.json": dump_json(
            _public_evaluation_contract(definition)
        ),
        ".hdp/source-definition.public.json": dump_json(
            _public_source_definition(definition)
        ),
        ".hdp/assumptions.md": _assumptions(definition),
        "STATE.md": _state_template(definition),
        "scripts/harnessctl.py": _harnessctl_script(),
        "evidence/README.md": "# Runtime evidence\n\nCommand records and logs are written here by `scripts/harnessctl.py`.\n",
        "evidence/ledger.jsonl": "",
    }
    files.update(_role_files(definition))
    source_map = _source_map(definition)
    source_map[f".agents/skills/{skill_name}/SKILL.md"] = source_map.pop(".agents/skills")
    source_map[f".agents/skills/{skill_name}/agents/openai.yaml"] = [
        "/metadata/title", "/purpose", "/runtime/profile"
    ]
    source_map["evidence/README.md"] = ["/observability/events", "/evaluation"]
    source_map["evidence/ledger.jsonl"] = ["/observability/events"]
    return files, source_map


def _public_source_definition(definition: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the exact declared HDP after canonical JSON normalisation.

    Definitions contain public evaluator contracts and opaque commitments, not
    evaluator-private cases, answers, credentials, or implementation code. The
    exact declared contract is therefore safe to reconstruct and remains a
    structurally valid input for analyse-to-compile round trips.
    """

    return json.loads(canonical_json(definition))


def _load_previous_manifest(output: Path) -> Dict[str, Any]:
    path = output / MANIFEST_PATH
    if not path.exists():
        if output.exists() and any(output.iterdir()):
            raise HdpGenerationError(
                f"refusing to generate into non-empty {output} without {MANIFEST_PATH}; "
                "choose an empty directory"
            )
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HdpGenerationError(f"cannot read previous generator manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise HdpGenerationError("previous generator manifest must be an object")
    if value.get("manifestVersion") != "1" or not isinstance(value.get("artifacts"), list):
        raise HdpGenerationError("previous generator manifest has an unsupported structure")
    seen: set[str] = set()
    for item in value["artifacts"]:
        if not isinstance(item, dict):
            raise HdpGenerationError("previous generator manifest artifact must be an object")
        relative = _safe_relative_path(item.get("path"), label="manifest artifact path")
        if (
            relative == MANIFEST_PATH.as_posix()
            or _is_manual_extension(relative)
            or relative in seen
        ):
            raise HdpGenerationError(f"invalid or duplicate manifest artifact path: {relative}")
        if not _SHA256.fullmatch(str(item.get("sha256", ""))):
            raise HdpGenerationError(f"invalid manifest artifact digest: {relative}")
        seen.add(relative)
    return value


def _check_manual_edits(
    output: Path, previous: Mapping[str, Any], new_paths: Sequence[str], force: bool
) -> List[str]:
    previous_artifacts = {
        item["path"]: item for item in previous.get("artifacts", []) if "path" in item
    }
    changed: List[str] = []
    for relative, record in previous_artifacts.items():
        path = _inside_output(output, relative)
        if path.exists() and (
            not path.is_file()
            or _sha256_bytes(path.read_bytes()) != record.get("sha256")
        ):
            changed.append(relative)
    if changed and not force:
        raise HdpGenerationError(
            "generated files contain manual edits; move changes under manual/ or rerun "
            f"with --force-generated: {', '.join(sorted(changed))}"
        )
    return sorted(set(previous_artifacts) - set(new_paths))


def _check_unmanaged_files(output: Path, previous: Mapping[str, Any]) -> None:
    if not previous:
        return
    managed = {
        item["path"] for item in previous.get("artifacts", [])
        if isinstance(item, Mapping) and isinstance(item.get("path"), str)
    }
    managed.add(MANIFEST_PATH.as_posix())
    unmanaged: List[str] = []
    for path in sorted(output.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(output).as_posix()
        if relative in managed or relative.startswith("manual/"):
            continue
        unmanaged.append(relative)
    if unmanaged:
        raise HdpGenerationError(
            "output contains unmanaged files outside manual/: " + ", ".join(unmanaged)
        )


def generate_harness(
    definition_path: Path,
    output: Path,
    *,
    force_generated: bool = False,
    additional_files: Mapping[str, str] | None = None,
    additional_source_map: Mapping[str, List[str]] | None = None,
    runtime_policy_overlay: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    definition_path = definition_path.resolve()
    output = _prepare_output_root(output)
    unknown_overlay = sorted(set(runtime_policy_overlay or {}) - _OVERLAY_KEYS)
    if unknown_overlay:
        raise HdpGenerationError(f"unsupported runtime policy overlay keys: {unknown_overlay}")

    definition = load_document(definition_path)
    diagnostics = structural_diagnostics(definition)
    if not diagnostics:
        from .semantic_validation import semantic_diagnostics

        diagnostics.extend(semantic_diagnostics(definition, definition_path.parent))
    if diagnostics:
        summary = "; ".join(
            f"{item.code} {item.instance_path or '/'}: {item.message}"
            for item in diagnostics[:10]
        )
        raise HdpGenerationError(f"definition is invalid: {summary}")

    reconstruction = definition.get("extensions", {}).get("x-hdp-reconstruction", {})
    if reconstruction and not reconstruction.get("generationReady", False):
        raise HdpGenerationError(
            "reconstructed definition is not generation-ready; resolve its blocking "
            "unknowns and obtain the required human confirmations"
        )

    if definition["runtime"]["profile"]["type"] != "codex-software-development":
        raise HdpGenerationError(
            "reference generator supports only runtime.profile.type "
            "codex-software-development"
        )

    files, source_map = _render_files(definition, runtime_policy_overlay)
    for relative, content in (additional_files or {}).items():
        relative = _safe_relative_path(relative, label="additional generated path")
        _inside_output(output, relative)
        if relative == MANIFEST_PATH.as_posix():
            raise HdpGenerationError(f"additional generated path is reserved: {relative}")
        if _is_manual_extension(relative):
            raise HdpGenerationError(
                f"additional generated path is under the manual extension root: {relative}"
            )
        if relative in files:
            raise HdpGenerationError(f"additional generated path conflicts with core output: {relative}")
        files[relative] = content
    normalized_source_map: Dict[str, List[str]] = {}
    for key, value in (additional_source_map or {}).items():
        normalized = _safe_relative_path(key, label="additional source-map path")
        if normalized not in files:
            raise HdpGenerationError(
                f"additional source-map path has no generated artifact: {normalized}"
            )
        normalized_source_map[normalized] = list(value)
    source_map.update(normalized_source_map)
    source_map[".hdp/source-map.json"] = ["factory-contract:/artifact-source-map"]
    unmapped = sorted(relative for relative in files if not source_map.get(relative))
    extra_mappings = sorted(set(source_map) - set(files) - {".hdp/source-map.json"})
    if unmapped or extra_mappings:
        raise HdpGenerationError(
            f"generated source map must be total; unmapped={unmapped}, extra={extra_mappings}"
        )
    files[".hdp/source-map.json"] = dump_json(source_map)
    for relative in files:
        _inside_output(output, relative)
    previous = _load_previous_manifest(output)
    _check_unmanaged_files(output, previous)
    stale = _check_manual_edits(output, previous, sorted(files), force_generated)

    output.mkdir(parents=True, exist_ok=True)
    for relative in sorted(files):
        mode = 0o755 if relative == "scripts/harnessctl.py" else 0o644
        atomic_write_text(_inside_output(output, relative), files[relative], mode=mode)

    # Delete only paths previously owned by the generator, and only after every
    # replacement write has succeeded. A failed deletion leaves the old manifest
    # in place, so the next run can retry deterministically.
    for relative in stale:
        stale_path = _inside_output(output, relative)
        if stale_path.exists():
            try:
                stale_path.unlink()
            except OSError as exc:
                raise HdpGenerationError(
                    f"cannot remove stale generated artifact {relative}: {exc}"
                ) from exc

    artifacts = [
        {
            "path": relative,
            "sha256": _sha256_text(files[relative]),
            "sourceFields": source_map.get(relative, []),
        }
        for relative in sorted(files)
    ]
    manifest: Dict[str, Any] = {
        "manifestVersion": "1",
        "generator": {"name": "hdp-reference", "version": __version__},
        "source": {
            "id": definition["metadata"]["id"],
            "version": definition["metadata"]["version"],
            "sha256": _sha256_text(canonical_json(definition)),
        },
        "artifacts": artifacts,
        "staleGeneratedArtifactsRetained": [],
        "manualExtensionRoot": "manual/",
    }
    atomic_write_text(_inside_output(output, MANIFEST_PATH.as_posix()), dump_json(manifest))
    return manifest
