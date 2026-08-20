"""Convention-driven Harness Factory project and installation helpers."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import importlib.resources
import json
import os
import secrets
import shutil
import stat
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .diagnostics import HdpInputError
from .io import atomic_write_text, dump_json, dump_yaml, load_document, load_document_bytes


INSTALL_MANIFEST = Path(".harness-factory/install-manifest.json")
INSTALL_LOCK = Path(".harness-factory/install.lock")
INSTALL_TRANSACTION = Path(".harness-factory/install-transaction.json")
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
_FILE_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_MAX_TRANSACTION_FILE_BYTES = 4 * 1024 * 1024


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    descriptor = os.open(
        path,
        os.O_RDONLY | _FILE_NOFOLLOW | getattr(os, "O_NONBLOCK", 0),
    )
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise HdpInputError(f"expected a regular file: {path}")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _safe_root(path: Path, *, label: str, must_exist: bool = True) -> Path:
    lexical = path.expanduser().absolute()
    if lexical.is_symlink():
        raise HdpInputError(f"{label} cannot be a symlink: {lexical}")
    resolved = lexical.resolve()
    if must_exist and not resolved.is_dir():
        raise HdpInputError(f"{label} is not a directory: {resolved}")
    return resolved


def _safe_relative(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise HdpInputError(f"unsafe managed artifact path: {value!r}")
    if candidate.as_posix() in {"", "."}:
        raise HdpInputError(f"unsafe managed artifact path: {value!r}")
    if candidate.parts[0] in {".git", ".harness-factory"}:
        raise HdpInputError(f"managed artifact path uses a reserved root: {value!r}")
    return candidate


def _safe_destination(root: Path, relative: Path) -> Path:
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise HdpInputError(
                f"managed installation refuses symlink destination: {relative.as_posix()}"
            )
    return root / relative


def _safe_source(root: Path, relative: Path) -> Path:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise HdpInputError(
                f"generated harness refuses symlink source: {relative.as_posix()}"
            )
    try:
        resolved = current.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HdpInputError(
            f"generated artifact is missing: {relative.as_posix()}"
        ) from exc
    if resolved != root and root not in resolved.parents:
        raise HdpInputError(
            f"generated artifact escapes harness root: {relative.as_posix()}"
        )
    if not stat.S_ISREG(resolved.lstat().st_mode):
        raise HdpInputError(
            f"generated artifact is not a regular file: {relative.as_posix()}"
        )
    return resolved


def _open_parent_fd(root_fd: int, relative: Path, *, create: bool) -> tuple[int, str]:
    current_fd = os.dup(root_fd)
    try:
        for part in relative.parent.parts:
            try:
                next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=current_fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o755, dir_fd=current_fd)
                next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=current_fd)
            except OSError as exc:
                raise HdpInputError(
                    f"managed installation refuses unsafe destination parent: {relative.as_posix()}"
                ) from exc
            os.close(current_fd)
            current_fd = next_fd
        return current_fd, relative.name
    except Exception:
        os.close(current_fd)
        raise


def _entry_at(root_fd: int, relative: Path) -> os.stat_result | None:
    try:
        parent_fd, name = _open_parent_fd(root_fd, relative, create=False)
    except FileNotFoundError:
        return None
    try:
        try:
            return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
    finally:
        os.close(parent_fd)


def _snapshot_at(
    root_fd: int,
    relative: Path,
    *,
    maximum: int = _MAX_TRANSACTION_FILE_BYTES,
) -> dict[str, Any] | None:
    try:
        parent_fd, name = _open_parent_fd(root_fd, relative, create=False)
    except FileNotFoundError:
        return None
    try:
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(metadata.st_mode):
            raise HdpInputError(
                f"managed installation refuses non-regular destination: {relative.as_posix()}"
            )
        if metadata.st_size > maximum:
            raise HdpInputError(
                f"managed installation file exceeds {maximum} bytes: {relative.as_posix()}"
            )
        descriptor = os.open(
            name,
            os.O_RDONLY | _FILE_NOFOLLOW | getattr(os, "O_NONBLOCK", 0),
            dir_fd=parent_fd,
        )
        try:
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining and (chunk := os.read(descriptor, min(1024 * 1024, remaining))):
                chunks.append(chunk)
                remaining -= len(chunk)
        finally:
            os.close(descriptor)
        content = b"".join(chunks)
        if len(content) > maximum or len(content) != metadata.st_size:
            raise HdpInputError(
                f"managed installation file changed while read: {relative.as_posix()}"
            )
        return {
            "content": content,
            "mode": stat.S_IMODE(metadata.st_mode),
            "sha256": _sha256_bytes(content),
        }
    finally:
        os.close(parent_fd)


def _atomic_write_at(
    root_fd: int,
    relative: Path,
    content: bytes,
    *,
    mode: int,
    allowed_current: set[str | None],
) -> None:
    current = _snapshot_at(root_fd, relative)
    current_digest = current["sha256"] if current is not None else None
    if current_digest not in allowed_current:
        raise HdpInputError(
            f"destination changed during installation: {relative.as_posix()}"
        )
    parent_fd, name = _open_parent_fd(root_fd, relative, create=True)
    temporary = f".{name}.harness-factory-{secrets.token_hex(8)}"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _FILE_NOFOLLOW,
            mode,
            dir_fd=parent_fd,
        )
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def _unlink_at(
    root_fd: int, relative: Path, *, allowed_current: set[str | None]
) -> None:
    current = _snapshot_at(root_fd, relative)
    digest = current["sha256"] if current is not None else None
    if digest not in allowed_current:
        raise HdpInputError(
            f"destination changed during transaction recovery: {relative.as_posix()}"
        )
    if current is None:
        return
    parent_fd, name = _open_parent_fd(root_fd, relative, create=False)
    try:
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


@contextmanager
def _target_lock(target: Path):
    root_fd = os.open(target, _DIRECTORY_FLAGS)
    parent_fd: int | None = None
    lock_fd: int | None = None
    try:
        parent_fd, name = _open_parent_fd(root_fd, INSTALL_LOCK, create=True)
        lock_fd = os.open(
            name, os.O_RDWR | os.O_CREAT | _FILE_NOFOLLOW, 0o600, dir_fd=parent_fd
        )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HdpInputError("another harness installation is already in progress") from exc
        yield root_fd
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if parent_fd is not None:
            os.close(parent_fd)
        os.close(root_fd)


def _journal_entry(path: str, snapshot: dict[str, Any] | None, new_digest: str) -> dict[str, Any]:
    original = None
    if snapshot is not None:
        original = {
            "sha256": snapshot["sha256"],
            "mode": snapshot["mode"],
            "contentBase64": base64.b64encode(snapshot["content"]).decode("ascii"),
        }
    return {"path": path, "newSha256": new_digest, "original": original}


def _recover_transaction(root_fd: int, *, expected_sha256: str) -> None:
    snapshot = _snapshot_at(root_fd, INSTALL_TRANSACTION)
    if snapshot is None:
        raise HdpInputError("installation transaction journal disappeared before recovery")
    if snapshot["sha256"] != expected_sha256:
        raise HdpInputError("installation transaction journal changed before recovery")
    try:
        value = json.loads(snapshot["content"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HdpInputError("installation transaction journal is malformed") from exc
    entries = value.get("entries") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {"schemaVersion", "kind", "entries"}
        or value.get("schemaVersion") != "1"
        or value.get("kind") != "HarnessInstallTransaction"
        or not isinstance(entries, list)
    ):
        raise HdpInputError("installation transaction journal is malformed")
    seen: set[str] = set()
    for item in reversed(entries):
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "newSha256", "original"}
            or not isinstance(item.get("path"), str)
            or not isinstance(item.get("newSha256"), str)
            or len(item["newSha256"]) != 64
            or any(character not in "0123456789abcdef" for character in item["newSha256"])
            or item["path"] in seen
        ):
            raise HdpInputError("installation transaction journal is malformed")
        seen.add(item["path"])
        relative = (
            INSTALL_MANIFEST
            if item["path"] == INSTALL_MANIFEST.as_posix()
            else _safe_relative(item["path"])
        )
        new_digest = item.get("newSha256")
        original = item.get("original")
        current = _snapshot_at(root_fd, relative)
        current_digest = current["sha256"] if current is not None else None
        if original is None:
            _unlink_at(root_fd, relative, allowed_current={None, new_digest})
            continue
        if not isinstance(original, dict):
            raise HdpInputError("installation transaction journal is malformed")
        try:
            content = base64.b64decode(original["contentBase64"], validate=True)
            original_digest = original["sha256"]
            mode = int(original["mode"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HdpInputError("installation transaction journal is malformed") from exc
        if set(original) != {"sha256", "mode", "contentBase64"}:
            raise HdpInputError("installation transaction journal is malformed")
        if len(content) > _MAX_TRANSACTION_FILE_BYTES or not 0 <= mode <= 0o777:
            raise HdpInputError("installation transaction journal backup is unsafe")
        if _sha256_bytes(content) != original_digest:
            raise HdpInputError("installation transaction journal backup digest is invalid")
        if current_digest not in {None, new_digest, original_digest}:
            raise HdpInputError(
                f"destination changed after interrupted installation: {relative.as_posix()}"
            )
        _atomic_write_at(
            root_fd,
            relative,
            content,
            mode=mode,
            allowed_current={None, new_digest, original_digest},
        )
    _unlink_at(
        root_fd,
        INSTALL_TRANSACTION,
        allowed_current={snapshot["sha256"]},
    )


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    definition: Path
    binding: Path
    build: Path
    analysis: Path
    release: Path
    evidence: Path


def resolve_project(root: Path) -> ProjectPaths:
    root = _safe_root(root, label="project")

    def choose(label: str, candidates: tuple[str, ...]) -> Path:
        matches = [root / candidate for candidate in candidates if (root / candidate).is_file()]
        if not matches:
            raise HdpInputError(
                f"cannot discover {label} under {root}; expected one of: "
                + ", ".join(candidates)
            )
        return matches[0]

    definition = choose(
        "HDP definition",
        ("harness/hdp.yaml", "harness/hdp.json", "hdp.yaml", "hdp.json"),
    )
    binding = choose(
        "Codex binding",
        (
            "harness/bindings/codex.yaml",
            "harness/bindings/codex.json",
            "bindings/codex.yaml",
            "bindings/codex.json",
        ),
    )
    return ProjectPaths(
        root=root,
        definition=definition,
        binding=binding,
        build=root / "build/harness",
        analysis=root / "build/analysis",
        release=root / "dist/harness-release",
        evidence=root / ".harness-factory/verification-bundle.json",
    )


def _template_text(relative: str) -> str:
    packaged = importlib.resources.files("hdp").joinpath(
        "templates", "codex-sdlc", relative
    )
    try:
        return packaged.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        repository_root = Path(__file__).resolve().parents[2]
        fallback = repository_root / "examples/software-development" / relative
        return fallback.read_text(encoding="utf-8")


def initialise_codex_sdlc(directory: Path) -> dict[str, Any]:
    lexical = directory.expanduser().absolute()
    if lexical.exists() and lexical.is_symlink():
        raise HdpInputError(f"initialization directory cannot be a symlink: {lexical}")
    if lexical.exists() and any(lexical.iterdir()):
        raise HdpInputError(f"initialization directory must be empty: {lexical}")
    lexical.mkdir(parents=True, exist_ok=True)
    project = lexical.resolve()
    definition = yaml.safe_load(_template_text("hdp.yaml"))
    slug = "-".join(
        part for part in project.name.lower().replace("_", "-").split("-") if part
    ) or "my-harness"
    definition["metadata"]["id"] = f"urn:hdp:local:{slug}"
    definition["metadata"]["name"] = slug
    definition["metadata"]["title"] = f"{project.name} software-development harness"
    atomic_write_text(project / "harness/hdp.yaml", dump_yaml(definition))
    atomic_write_text(
        project / "harness/bindings/codex.yaml", _template_text("bindings/codex.yaml")
    )
    atomic_write_text(
        project / "README.md",
        "# Harness project\n\n"
        "This project was initialized from the conservative `codex-sdlc` template. "
        "Review the declared outcomes, permissions, tools, tests and ownership before "
        "installing it into a repository.\n\n"
        "```bash\n"
        "harness build\n"
        "harness install ../target-repository --dry-run\n"
        "```\n",
    )
    return {
        "status": "initialized",
        "template": "codex-sdlc",
        "directory": str(project),
        "definition": "harness/hdp.yaml",
        "binding": "harness/bindings/codex.yaml",
    }


def _managed_sources(harness: Path) -> tuple[dict[str, Any], list[tuple[Path, Path]]]:
    harness = _safe_root(harness, label="generated harness")
    manifest_relative = Path(".hdp/manifest.json")
    root_fd = os.open(harness, _DIRECTORY_FLAGS)
    try:
        manifest_snapshot = _snapshot_at(
            root_fd, manifest_relative, maximum=1_048_576
        )
    finally:
        os.close(root_fd)
    if manifest_snapshot is None:
        raise HdpInputError("generated harness manifest is missing")
    manifest = load_document_bytes(
        manifest_snapshot["content"],
        suffix=".json",
        label="generated harness manifest",
    )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise HdpInputError("generated harness manifest has no artifact array")
    relative_paths: list[Path] = []
    seen: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise HdpInputError("generated harness manifest contains an invalid artifact")
        relative = _safe_relative(item["path"])
        key = relative.as_posix()
        if relative == manifest_relative:
            raise HdpInputError(
                "generated artifact manifest cannot list its own manifest file"
            )
        if key in seen:
            raise HdpInputError(f"duplicate generated artifact path: {key}")
        seen.add(key)
        source = _safe_source(harness, relative)
        if not source.is_file():
            raise HdpInputError(f"generated artifact is not a regular file: {key}")
        if _sha256_path(source) != item.get("sha256"):
            raise HdpInputError(f"generated artifact digest mismatch: {key}")
        relative_paths.append(relative)
    relative_paths.append(manifest_relative)
    return manifest, [
        (relative, _safe_source(harness, relative)) for relative in relative_paths
    ]


def install_harness(harness: Path, target: Path, *, dry_run: bool) -> dict[str, Any]:
    target = _safe_root(target, label="target repository")
    manifest, sources = _managed_sources(harness)
    pending_journal = _safe_destination(target, INSTALL_TRANSACTION)
    if dry_run and pending_journal.exists():
        return {
            "status": "conflict",
            "dryRun": True,
            "target": str(target),
            "source": str(Path(harness).resolve()),
            "sourceDefinition": manifest.get("source", {}),
            "actions": [],
            "conflicts": [{
                "path": INSTALL_TRANSACTION.as_posix(),
                "reason": "an unfinished installation requires explicit manual recovery",
            }],
        }
    lock_context = nullcontext(None) if dry_run else _target_lock(target)
    with lock_context as root_fd:
        if root_fd is not None and _entry_at(root_fd, INSTALL_TRANSACTION) is not None:
            raise HdpInputError(
                "an unfinished installation journal exists; inspect the target and "
                "remove it only after explicit manual recovery"
            )

        install_manifest_path = _safe_destination(target, INSTALL_MANIFEST)
        previous: dict[str, Any] = {}
        if root_fd is None:
            if install_manifest_path.exists():
                if install_manifest_path.is_symlink():
                    raise HdpInputError("installation manifest cannot be a symlink")
                previous = load_document(install_manifest_path)
        else:
            previous_snapshot = _snapshot_at(root_fd, INSTALL_MANIFEST)
            if previous_snapshot is not None:
                try:
                    previous = json.loads(previous_snapshot["content"].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise HdpInputError("installation manifest is malformed") from exc
        if previous and previous.get("manifestVersion") != "1":
            raise HdpInputError("unsupported or malformed installation manifest")
        previous_files = {
            item["path"]: item["sha256"]
            for item in previous.get("files", [])
            if isinstance(item, dict)
            and isinstance(item.get("path"), str)
            and isinstance(item.get("sha256"), str)
        }

        actions: list[dict[str, str]] = []
        conflicts: list[dict[str, str]] = []
        installed: list[dict[str, str]] = []
        for relative, source in sources:
            key = relative.as_posix()
            destination = _safe_destination(target, relative)
            source_digest = _sha256_path(source)
            installed.append({"path": key, "sha256": source_digest})
            if not destination.exists():
                action = "create"
            elif not destination.is_file():
                conflicts.append({"path": key, "reason": "destination is not a regular file"})
                continue
            else:
                current_digest = _sha256_path(destination)
                if key not in previous_files:
                    conflicts.append(
                        {"path": key, "reason": "existing file is unowned, even if content is identical"}
                    )
                    continue
                if previous_files[key] != current_digest:
                    conflicts.append(
                        {"path": key, "reason": "existing managed file is locally modified"}
                    )
                    continue
                action = "unchanged" if current_digest == source_digest else "update"
            actions.append({"path": key, "action": action})

        current_paths = {relative.as_posix() for relative, _ in sources}
        for stale_path, stale_digest in sorted(previous_files.items()):
            if stale_path in current_paths:
                continue
            relative = _safe_relative(stale_path)
            destination = _safe_destination(target, relative)
            if not destination.exists():
                continue
            if not destination.is_file() or _sha256_path(destination) != stale_digest:
                reason = "previously managed file is locally modified"
            else:
                reason = "previously managed file is no longer generated; remove it explicitly"
            conflicts.append({"path": stale_path, "reason": reason})

        result = {
            "status": "conflict" if conflicts else "planned" if dry_run else "installed",
            "dryRun": dry_run,
            "target": str(target),
            "source": str(Path(harness).resolve()),
            "sourceDefinition": manifest.get("source", {}),
            "actions": actions,
            "conflicts": conflicts,
        }
        if conflicts or dry_run:
            return result
        assert root_fd is not None

        source_by_path = {relative.as_posix(): source for relative, source in sources}
        digest_by_path = {item["path"]: item["sha256"] for item in installed}
        writes: list[dict[str, Any]] = []
        journal_entries: list[dict[str, Any]] = []
        for action in actions:
            relative = _safe_relative(action["path"])
            snapshot = _snapshot_at(root_fd, relative)
            current_digest = snapshot["sha256"] if snapshot is not None else None
            expected_current = None if action["action"] == "create" else previous_files[action["path"]]
            if current_digest != expected_current:
                raise HdpInputError(
                    f"destination changed during installation: {action['path']}"
                )
            source = source_by_path[action["path"]]
            content = source.read_bytes()
            if _sha256_bytes(content) != digest_by_path[action["path"]]:
                raise HdpInputError(
                    f"generated artifact changed during installation: {action['path']}"
                )
            if action["action"] != "unchanged":
                writes.append({
                    "path": relative,
                    "content": content,
                    "mode": stat.S_IMODE(source.stat().st_mode),
                    "allowed": {expected_current},
                })
                journal_entries.append(
                    _journal_entry(action["path"], snapshot, digest_by_path[action["path"]])
                )

        install_manifest = {
            "manifestVersion": "1",
            "sourceDefinition": manifest.get("source", {}),
            "sourceGenerator": manifest.get("generator", {}),
            "files": installed,
        }
        manifest_content = dump_json(install_manifest).encode("utf-8")
        manifest_snapshot = _snapshot_at(root_fd, INSTALL_MANIFEST)
        manifest_current = (
            manifest_snapshot["sha256"] if manifest_snapshot is not None else None
        )
        manifest_digest = _sha256_bytes(manifest_content)
        writes.append({
            "path": INSTALL_MANIFEST,
            "content": manifest_content,
            "mode": 0o644,
            "allowed": {manifest_current},
        })
        journal_entries.append(
            _journal_entry(INSTALL_MANIFEST.as_posix(), manifest_snapshot, manifest_digest)
        )
        if len(journal_entries) > 1024:
            raise HdpInputError("installation transaction exceeds 1024 managed writes")
        journal = dump_json({
            "schemaVersion": "1",
            "kind": "HarnessInstallTransaction",
            "entries": journal_entries,
        }).encode("utf-8")
        if len(journal) > _MAX_TRANSACTION_FILE_BYTES:
            raise HdpInputError(
                "installation transaction journal exceeds the 4 MiB safety limit"
            )
        _atomic_write_at(
            root_fd,
            INSTALL_TRANSACTION,
            journal,
            mode=0o600,
            allowed_current={None},
        )
        journal_digest = _sha256_bytes(journal)
        try:
            for write in writes:
                _atomic_write_at(
                    root_fd,
                    write["path"],
                    write["content"],
                    mode=write["mode"],
                    allowed_current=write["allowed"],
                )
        except Exception:
            _recover_transaction(root_fd, expected_sha256=journal_digest)
            raise
        transaction = _snapshot_at(root_fd, INSTALL_TRANSACTION)
        _unlink_at(
            root_fd,
            INSTALL_TRANSACTION,
            allowed_current={transaction["sha256"] if transaction else None},
        )
        return result


def executable_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"name": name, "available": path is not None, "path": path}
