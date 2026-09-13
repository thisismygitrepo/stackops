from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tomllib
from typing import cast

from stackops.scripts.python.helpers.helpers_devops.stackops_versioning import get_next_stackops_version


@dataclass(frozen=True)
class StackOpsRelease:
    previous_version: str
    version: str
    changed_files: tuple[Path, ...]


@dataclass(frozen=True)
class SourceVersionEdit:
    path: Path
    content: bytes


def read_stackops_project(repo_root: Path) -> dict[str, object]:
    metadata = cast(dict[str, object], tomllib.loads(repo_root.joinpath("pyproject.toml").read_text(encoding="utf-8")))
    project = metadata.get("project")
    if not isinstance(project, dict):
        raise ValueError("StackOps pyproject.toml must contain a project table.")
    return cast(dict[str, object], project)


def is_stackops_repository(repo_root: Path) -> bool:
    pyproject = repo_root / "pyproject.toml"
    if not repo_root.is_dir() or pyproject.is_symlink() or not pyproject.is_file() or shutil.which("git") is None:
        return False
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=repo_root, check=False, capture_output=True, text=True)
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != repo_root.resolve():
        return False
    try:
        project = read_stackops_project(repo_root=repo_root)
    except (tomllib.TOMLDecodeError, ValueError):
        return False
    return project.get("name") == "stackops"


def plan_source_version_edits(repo_root: Path, tracked_files: tuple[Path, ...], version: str) -> tuple[SourceVersionEdit, ...]:
    requirement_pattern = re.compile(
        r"(?<![A-Za-z0-9_.-])(?P<prefix>stackops(?:\[[A-Za-z0-9_, .-]+\])?\s*>=\s*)"
        r"[0-9]+(?:\.[0-9]+)+(?![A-Za-z0-9_.+!-])"
    )
    assignment_pattern = re.compile(
        r"""(?<![A-Za-z0-9_])(?P<prefix>STACKOPS_VERSION(?:\s*:\s*str)?\s*=\s*)(?P<quote>["'])"""
        r"[0-9]+(?:\.[0-9]+)+(?P=quote)"
    )
    edits: list[SourceVersionEdit] = []
    for relative_path in tracked_files:
        managed_root = relative_path.parts[:2] == ("src", "stackops") or relative_path.parts[0] in {"jobs", "scripts"}
        root_dockerfile = len(relative_path.parts) == 1 and relative_path.name.startswith("Dockerfile")
        source_file = relative_path.suffix in {".py", ".sh", ".ps1"} or relative_path.name.startswith("Dockerfile")
        if not source_file or not (managed_root or root_dockerfile) or {".venv", "venv"}.intersection(relative_path.parts):
            continue
        path = repo_root / relative_path
        if any((repo_root / part).is_symlink() for part in (relative_path, *relative_path.parents)):
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            continue
        content = path.read_bytes().decode("utf-8")
        updated = requirement_pattern.sub(rf"\g<prefix>{version}", content)
        updated = assignment_pattern.sub(rf"\g<prefix>\g<quote>{version}\g<quote>", updated)
        if updated != content:
            edits.append(SourceVersionEdit(path=relative_path, content=updated.encode("utf-8")))
    return tuple(edits)


def bump_stackops_version(repo_root: Path, today: date) -> StackOpsRelease:
    if not is_stackops_repository(repo_root=repo_root):
        raise ValueError(f"Expected a StackOps Git checkout at {repo_root}.")
    project = read_stackops_project(repo_root=repo_root)
    previous_version = project.get("version")
    if not isinstance(previous_version, str):
        raise ValueError("StackOps pyproject.toml must contain a string project.version.")
    version = get_next_stackops_version(current_version=previous_version, today=today)
    tracked_result = subprocess.run(["git", "ls-files", "-z"], cwd=repo_root, check=True, capture_output=True, text=True)
    tracked_files = tuple(Path(name) for name in tracked_result.stdout.split("\0") if name)
    metadata_paths = (Path("pyproject.toml"), Path("uv.lock"))
    metadata_before: dict[Path, bytes] = {}
    for relative_path in metadata_paths:
        path = repo_root / relative_path
        if relative_path not in tracked_files or path.is_symlink() or not path.is_file():
            raise ValueError(f"Release metadata must be a tracked regular file: {relative_path}.")
        metadata_before[relative_path] = path.read_bytes()
    edits = plan_source_version_edits(repo_root=repo_root, tracked_files=tracked_files, version=version)
    subprocess.run(["uv", "version", version, "--no-sync"], cwd=repo_root, check=True)
    for edit in edits:
        repo_root.joinpath(edit.path).write_bytes(edit.content)
    subprocess.run(["uv", "sync"], cwd=repo_root, check=True)
    changed_metadata = tuple(path for path, original in metadata_before.items() if repo_root.joinpath(path).read_bytes() != original)
    return StackOpsRelease(previous_version=previous_version, version=version, changed_files=(*changed_metadata, *(edit.path for edit in edits)))
