from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "src" / "hdp"
FORBIDDEN_SEGMENTS = {
    "build",
    "dist",
    "evaluator",
    "evidence",
    "fixtures",
    "workstreams",
}
FORBIDDEN_MARKERS = ("canary", "gold", "private")


def _source_package_files(prefix: str) -> set[str]:
    return {
        f"{prefix}/{path.relative_to(PACKAGE_ROOT).as_posix()}"
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


def _sdist_files(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        files = {member.name for member in archive.getmembers() if member.isfile()}
    roots = {PurePosixPath(name).parts[0] for name in files}
    assert len(roots) == 1
    root = roots.pop()
    return {name.removeprefix(f"{root}/") for name in files}


def _wheel_files(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return {name for name in archive.namelist() if not name.endswith("/")}


def _assert_no_private_build_inputs(paths: set[str]) -> None:
    for path in paths:
        lowered = path.lower()
        segments = set(PurePosixPath(lowered).parts)
        assert segments.isdisjoint(FORBIDDEN_SEGMENTS), path
        assert not any(marker in lowered for marker in FORBIDDEN_MARKERS), path


def test_built_distributions_contain_only_public_package_files(tmp_path: Path) -> None:
    subprocess.run(
        [
            "uv",
            "build",
            "--out-dir",
            str(tmp_path),
            "--no-build-logs",
            "--no-create-gitignore",
            str(ROOT),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    wheels = list(tmp_path.glob("*.whl"))
    sdists = list(tmp_path.glob("*.tar.gz"))
    assert len(wheels) == 1
    assert len(sdists) == 1

    wheel_files = _wheel_files(wheels[0])
    sdist_files = _sdist_files(sdists[0])
    wheel_package_files = {
        path for path in wheel_files if ".dist-info/" not in path
    }
    sdist_package_files = {path for path in sdist_files if path.startswith("src/")}

    expected_wheel_files = _source_package_files("hdp")
    expected_sdist_package_files = _source_package_files("src/hdp")
    assert wheel_package_files == expected_wheel_files
    assert sdist_package_files == expected_sdist_package_files
    assert "hdp/schemas/hdp.schema.json" in wheel_files
    assert "src/hdp/schemas/hdp.schema.json" in sdist_files

    allowed_sdist_roots = {
        ".gitignore",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "pyproject.toml",
        "src",
    }
    assert {PurePosixPath(path).parts[0] for path in sdist_files} <= allowed_sdist_roots
    _assert_no_private_build_inputs(wheel_files)
    _assert_no_private_build_inputs(sdist_files)
