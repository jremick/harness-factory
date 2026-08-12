#!/usr/bin/env python3
"""Least-privilege process boundary for release-notes candidate code."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MAX_OUTPUT_BYTES = 1_048_576
DEFAULT_TIMEOUT_SECONDS = 15


class SandboxUnavailable(RuntimeError):
    """Raised when no supported least-privilege child sandbox is available."""


class SandboxExecutionError(RuntimeError):
    """Raised when a sandboxed child violates the bounded process protocol."""


@dataclass(frozen=True)
class BoundedResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _python_read_roots() -> list[Path]:
    roots = {
        Path(sys.prefix).absolute(),
        Path(sys.base_prefix).absolute(),
    }
    executable = Path(sys.executable).absolute()
    pending = [executable]
    seen: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for ancestor in (current, *current.parents):
            if ancestor.is_symlink():
                target = Path(os.readlink(ancestor))
                if not target.is_absolute():
                    target = ancestor.parent / target
                target = target.absolute()
                pending.append(target)
                # Python executables live below <installation>/bin.
                if target.parent.name == "bin":
                    roots.add(target.parent.parent)
                else:
                    roots.add(target)
        resolved = current.resolve()
        if resolved.parent.name == "bin":
            roots.add(resolved.parent.parent)
    return sorted(roots, key=lambda item: str(item))


def _sbpl_string(path: Path) -> str:
    return json.dumps(str(path), ensure_ascii=True)


class SandboxBoundary:
    """Execute untrusted Python with workspace-read-only access on macOS."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.sandbox_executable = Path("/usr/bin/sandbox-exec")
        self.python_roots = _python_read_roots()

    @property
    def available(self) -> bool:
        return platform.system() == "Darwin" and self.sandbox_executable.is_file()

    @property
    def mechanism(self) -> str:
        return "macos-sandbox-exec" if self.available else "unavailable"

    def describe(self) -> dict[str, Any]:
        reason = None
        if platform.system() != "Darwin":
            reason = "the release-notes evaluator currently requires macOS sandbox-exec"
        elif not self.sandbox_executable.is_file():
            reason = "/usr/bin/sandbox-exec is unavailable"
        return {
            "available": self.available,
            "mechanism": self.mechanism,
            "defaultPolicy": "deny",
            "network": "deny",
            "childProcess": "deny-fork",
            "workspace": "read-only",
            "privateEvaluator": "not allowlisted",
            "reason": reason,
        }

    def profile(self) -> str:
        read_roots = [self.workspace, *self.python_roots]
        exec_rules = "\n".join(
            f"  (subpath {_sbpl_string(root)})" for root in self.python_roots
        )
        ancestor_rules = "\n".join(
            f"  (path-ancestors {_sbpl_string(root)})" for root in read_roots
        )
        read_rules = "\n".join(
            f"  (subpath {_sbpl_string(root)})" for root in read_roots
        )
        return (
            '(version 1)\n'
            '(deny default)\n'
            '(import "system.sb")\n'
            '(deny network*)\n'
            '(deny mach-lookup)\n'
            '(deny mach-register)\n'
            '(deny ipc-posix-shm)\n'
            '(deny iokit-open-user-client)\n'
            '(deny iokit-get-properties)\n'
            '(allow process-exec\n'
            f'{exec_rules})\n'
            '(allow file-read-metadata file-test-existence\n'
            f'{ancestor_rules})\n'
            '(allow file-read* file-test-existence file-map-executable\n'
            f'{read_rules})\n'
        )

    def command(self, child_argv: list[str]) -> list[str]:
        if not self.available:
            description = self.describe()
            raise SandboxUnavailable(str(description["reason"]))
        return [str(self.sandbox_executable), "-p", self.profile(), *child_argv]

    def environment(self) -> dict[str, str]:
        return {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_CTYPE": "UTF-8",
            "PATH": str(Path(sys.executable).absolute().parent),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }

    def run(
        self,
        child_argv: list[str],
        *,
        input_bytes: bytes = b"",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> BoundedResult:
        argv = self.command(child_argv)

        def apply_limits() -> None:
            resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
            resource.setrlimit(
                resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES)
            )
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))

        with tempfile.TemporaryFile() as stdout_handle, tempfile.TemporaryFile() as stderr_handle:
            process = subprocess.Popen(
                argv,
                cwd=self.workspace,
                env=self.environment(),
                stdin=subprocess.PIPE,
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=True,
                preexec_fn=apply_limits,
            )
            timed_out = False
            try:
                process.communicate(input_bytes, timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            stdout_handle.seek(0)
            stderr_handle.seek(0)
            stdout = stdout_handle.read(MAX_OUTPUT_BYTES + 1)
            stderr = stderr_handle.read(MAX_OUTPUT_BYTES + 1)
        output_limited = len(stdout) > MAX_OUTPUT_BYTES or len(stderr) > MAX_OUTPUT_BYTES
        return BoundedResult(
            returncode=process.returncode,
            stdout=stdout[:MAX_OUTPUT_BYTES],
            stderr=stderr[:MAX_OUTPUT_BYTES],
            timed_out=timed_out,
            output_limited=output_limited,
        )


CANDIDATE_RUNNER = r'''
import builtins
import copy
import json
import os
import sys

protocol_input = sys.stdin
protocol_output = sys.stdout
value_error_type = builtins.ValueError
sys.path.insert(0, os.getcwd())

try:
    from src.release_notes import build_release_notes
except BaseException as exc:
    protocol_output.write(json.dumps({
        "event": "ready", "ok": False,
        "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
    }, separators=(",", ":")) + "\n")
    protocol_output.flush()
    raise SystemExit(70)

protocol_output.write('{"event":"ready","ok":true}\n')
protocol_output.flush()

def decode_argument(argument):
    encoding = argument.get("encoding")
    if encoding == "json":
        return argument.get("value")
    if encoding == "tuple":
        return tuple(argument.get("items", []))
    raise RuntimeError("unsupported argument encoding")

for line in protocol_input:
    try:
        request = json.loads(line)
        if set(request) != {"id", "operation", "argument"}:
            raise RuntimeError("invalid request shape")
        if request["operation"] != "build_release_notes":
            raise RuntimeError("unsupported operation")
        argument = decode_argument(request["argument"])
        original = copy.deepcopy(argument)
        try:
            value = build_release_notes(argument)
        except BaseException as exc:
            response = {
                "id": request["id"], "ok": False,
                "error": {
                    "type": type(exc).__name__,
                    "isValueError": isinstance(exc, value_error_type),
                    "message": str(exc)[:500],
                },
                "inputMutated": argument != original,
            }
        else:
            response = {
                "id": request["id"], "ok": True, "value": value,
                "inputMutated": argument != original,
            }
    except BaseException as exc:
        response = {
            "id": None, "ok": False,
            "protocolError": {"type": type(exc).__name__, "message": str(exc)[:500]},
        }
    protocol_output.write(json.dumps(response, separators=(",", ":")) + "\n")
    protocol_output.flush()
'''


CONTROL_PROBE_RUNNER = r'''
import errno
import json
import socket
import sys

request = json.loads(sys.stdin.readline())
denied_errnos = {errno.EACCES, errno.EPERM, errno.EROFS}

def outcome(name, action):
    try:
        action()
    except OSError as exc:
        return {
            "id": name, "denied": exc.errno in denied_errnos,
            "errno": exc.errno, "errorType": type(exc).__name__,
        }
    except BaseException as exc:
        return {"id": name, "denied": False, "errorType": type(exc).__name__}
    return {"id": name, "denied": False, "errorType": None}

results = []
try:
    with open(request["workspaceRead"], "rb") as stream:
        stream.read(1)
except BaseException as exc:
    results.append({"id": "workspace-read", "allowed": False, "errorType": type(exc).__name__})
else:
    results.append({"id": "workspace-read", "allowed": True, "errorType": None})

results.append(outcome(
    "private-evaluator-read", lambda: open(request["privateRead"], "rb").close()
))
results.append(outcome(
    "private-evaluator-write", lambda: open(request["privateWrite"], "rb+").close()
))
results.append(outcome("parent-read", lambda: open(request["parentRead"], "rb").close()))
results.append(outcome("workspace-write", lambda: open(request["workspaceWrite"], "rb+").close()))
results.append(outcome(
    "network-connect", lambda: socket.create_connection(("127.0.0.1", 9), 0.25).close()
))
results.append(outcome("process-fork", lambda: __import__("os").fork()))
sys.stdout.write(json.dumps({"results": results}, separators=(",", ":")) + "\n")
'''


def run_candidate_requests(
    boundary: SandboxBoundary,
    requests: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    payload = b"".join(
        json.dumps(item, separators=(",", ":")).encode("utf-8") + b"\n"
        for item in requests
    )
    child = boundary.run(
        [sys.executable, "-I", "-c", CANDIDATE_RUNNER], input_bytes=payload
    )
    metadata = {
        "exitCode": child.returncode,
        "timedOut": child.timed_out,
        "outputLimited": child.output_limited,
        "stderrSha256": sha256_bytes(child.stderr),
    }
    if child.timed_out:
        raise SandboxExecutionError("candidate child timed out")
    if child.output_limited:
        raise SandboxExecutionError("candidate child exceeded the output limit")
    lines = child.stdout.decode("utf-8", errors="strict").splitlines()
    if not lines:
        raise SandboxExecutionError("candidate child produced no protocol response")
    try:
        ready = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise SandboxExecutionError("candidate child produced non-JSON output") from exc
    if ready != {"event": "ready", "ok": True}:
        raise SandboxExecutionError(f"candidate import failed: {ready!r}")
    if child.returncode != 0:
        raise SandboxExecutionError(
            f"candidate child exited {child.returncode}: "
            f"{child.stderr.decode('utf-8', errors='replace')[:500]}"
        )
    responses: dict[str, dict[str, Any]] = {}
    for line in lines[1:]:
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SandboxExecutionError("candidate child produced non-JSON output") from exc
        response_id = response.get("id")
        if not isinstance(response_id, str) or response_id in responses:
            raise SandboxExecutionError("candidate child returned an invalid response ID")
        responses[response_id] = response
    expected_ids = {item["id"] for item in requests}
    if set(responses) != expected_ids:
        raise SandboxExecutionError("candidate child response IDs did not match requests")
    return responses, metadata


def run_control_probes(
    boundary: SandboxBoundary,
    *,
    workspace_read: Path,
    workspace_write: Path,
    private_path: Path,
    parent_path: Path,
) -> dict[str, Any]:
    request = {
        "workspaceRead": str(workspace_read.resolve()),
        "workspaceWrite": str(workspace_write.resolve()),
        "privateRead": str(private_path.resolve()),
        "privateWrite": str(private_path.resolve()),
        "parentRead": str(parent_path.resolve()),
    }
    child = boundary.run(
        [sys.executable, "-I", "-c", CONTROL_PROBE_RUNNER],
        input_bytes=json.dumps(request, separators=(",", ":")).encode("utf-8") + b"\n",
    )
    if child.timed_out or child.output_limited or child.returncode != 0:
        return {
            "passed": False,
            "exitCode": child.returncode,
            "timedOut": child.timed_out,
            "outputLimited": child.output_limited,
            "stderrSha256": sha256_bytes(child.stderr),
            "results": [],
        }
    try:
        payload = json.loads(child.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "passed": False,
            "exitCode": child.returncode,
            "timedOut": False,
            "outputLimited": False,
            "stderrSha256": sha256_bytes(child.stderr),
            "results": [],
        }
    results = payload.get("results", [])
    expected_denials = {
        "private-evaluator-read",
        "private-evaluator-write",
        "parent-read",
        "workspace-write",
        "network-connect",
        "process-fork",
    }
    observed_denials = {
        item.get("id") for item in results if item.get("denied") is True
    }
    workspace_allowed = any(
        item.get("id") == "workspace-read" and item.get("allowed") is True
        for item in results
    )
    return {
        "passed": workspace_allowed and observed_denials == expected_denials,
        "exitCode": child.returncode,
        "timedOut": False,
        "outputLimited": False,
        "stderrSha256": sha256_bytes(child.stderr),
        "results": results,
    }


def safe_workspace_file(workspace: Path, relative: str) -> tuple[Path | None, str | None]:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, "path is not workspace-relative"
    path = workspace / candidate
    current = path
    while current != workspace:
        if current.is_symlink():
            return None, "path traverses a symlink"
        current = current.parent
    if not path.is_file():
        return None, "path is not a regular file"
    return path, None


def inspect_ledger(
    workspace: Path,
    *,
    required_requirement_id: str,
    required_command_fragment: Iterable[str],
) -> dict[str, Any]:
    ledger_path, path_error = safe_workspace_file(workspace, "evidence/ledger.jsonl")
    if ledger_path is None:
        return {
            "valid": False,
            "errors": [path_error or "missing ledger"],
            "recordCount": 0,
            "requiredPassingCommandFound": False,
            "ledgerSha256": None,
            "verifiedLogDigests": [],
        }
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        ledger_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"ledger line {line_number} is not valid JSON")
            continue
        if not isinstance(item, dict):
            errors.append(f"ledger line {line_number} is not an object")
            continue
        records.append(item)
    verified_logs: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if record.get("sequence") != index:
            errors.append(f"ledger sequence {index} is not contiguous")
        command = record.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            errors.append(f"ledger record {index} has an invalid command")
        requirement_ids = record.get("requirementIds")
        if not isinstance(requirement_ids, list) or not all(
            isinstance(item, str) for item in requirement_ids
        ):
            errors.append(f"ledger record {index} has invalid requirement IDs")
        exit_code = record.get("exitCode")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            errors.append(f"ledger record {index} has an invalid exit code")
        for stream_name in ("stdout", "stderr"):
            artifact = record.get(stream_name)
            if not isinstance(artifact, dict):
                errors.append(f"ledger record {index} has no {stream_name} artifact")
                continue
            relative = artifact.get("path")
            expected_sha = artifact.get("sha256")
            if not isinstance(relative, str) or not isinstance(expected_sha, str):
                errors.append(f"ledger record {index} has an invalid {stream_name} artifact")
                continue
            log_path, log_error = safe_workspace_file(workspace, relative)
            if log_path is None:
                errors.append(f"ledger record {index} {stream_name}: {log_error}")
                continue
            actual_sha = sha256_file(log_path)
            if actual_sha != expected_sha:
                errors.append(f"ledger record {index} {stream_name} digest mismatch")
                continue
            verified_logs.append(
                {"path": relative, "sha256": actual_sha, "recordSequence": index}
            )
    fragment = tuple(required_command_fragment)
    required_match = False
    for record in records:
        command = record.get("command")
        requirements = record.get("requirementIds")
        if (
            isinstance(command, list)
            and record.get("exitCode") == 0
            and isinstance(requirements, list)
            and required_requirement_id in requirements
            and command
            and Path(command[0]).name in {"python", "python3", "python3.12"}
            and all(part in command for part in fragment)
        ):
            required_match = True
            break
    return {
        "valid": not errors and bool(records) and required_match,
        "errors": errors,
        "recordCount": len(records),
        "requiredPassingCommandFound": required_match,
        "ledgerSha256": sha256_file(ledger_path),
        "verifiedLogDigests": verified_logs,
    }


def inspect_manifest(workspace: Path) -> dict[str, Any]:
    manifest_path, manifest_error = safe_workspace_file(workspace, ".hdp/manifest.json")
    if manifest_path is None:
        return {
            "valid": False,
            "errors": [manifest_error or "missing manifest"],
            "manifestSha256": None,
            "verifiedArtifacts": [],
        }
    errors: list[str] = []
    verified: list[dict[str, str]] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "valid": False,
            "errors": ["manifest is not valid JSON"],
            "manifestSha256": sha256_file(manifest_path),
            "verifiedArtifacts": [],
        }
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("manifest artifacts are missing")
        artifacts = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append("manifest contains a non-object artifact")
            continue
        relative = artifact.get("path")
        expected_sha = artifact.get("sha256")
        if relative == "evidence/ledger.jsonl":
            # The generated manifest commits the ledger's initial empty state.
            continue
        if not isinstance(relative, str) or not isinstance(expected_sha, str):
            errors.append("manifest contains an invalid artifact commitment")
            continue
        path, path_error = safe_workspace_file(workspace, relative)
        if path is None:
            errors.append(f"manifest artifact {relative!r}: {path_error}")
            continue
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha:
            errors.append(f"manifest artifact {relative!r} digest mismatch")
            continue
        verified.append({"path": relative, "sha256": actual_sha})
    return {
        "valid": not errors and bool(verified),
        "errors": errors,
        "manifestSha256": sha256_file(manifest_path),
        "verifiedArtifacts": verified,
    }


def hash_tree(root: Path) -> tuple[str, dict[str, dict[str, Any]]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        directory_names.sort()
        file_names.sort()
        for name in list(directory_names):
            path = directory_path / name
            if path.is_symlink():
                snapshot[path.relative_to(root).as_posix()] = {
                    "type": "symlink",
                    "target": os.readlink(path),
                }
                directory_names.remove(name)
        for name in file_names:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                snapshot[relative] = {"type": "symlink", "target": os.readlink(path)}
            elif path.is_file():
                snapshot[relative] = {"type": "file", "sha256": sha256_file(path)}
            else:
                snapshot[relative] = {"type": "other"}
    canonical = json.dumps(snapshot, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256_bytes(canonical), snapshot


def scan_canary(workspace: Path, canary: str) -> list[str]:
    leaks: list[str] = []
    for directory, directory_names, file_names in os.walk(workspace, followlinks=False):
        directory_path = Path(directory)
        directory_names[:] = [
            name for name in directory_names if not (directory_path / name).is_symlink()
        ]
        for name in file_names:
            path = directory_path / name
            if path.is_symlink() or not path.is_file():
                continue
            if canary in path.read_text(encoding="utf-8", errors="ignore"):
                leaks.append(path.relative_to(workspace).as_posix())
    return sorted(leaks)


def capture_bounded(
    boundary: SandboxBoundary,
    child_argv: list[str],
) -> BoundedResult:
    return boundary.run(child_argv)
