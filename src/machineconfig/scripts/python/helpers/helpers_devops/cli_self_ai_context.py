from pathlib import Path
import subprocess

from machineconfig.utils.source_of_truth import EXCLUDE_DIRS


_ADDITIONAL_EXCLUDED_CONTEXT_PARTS = frozenset({"tests"})
_EXCLUDED_CONTEXT_PARTS = frozenset(entry for entry in EXCLUDE_DIRS if "/" not in entry) | _ADDITIONAL_EXCLUDED_CONTEXT_PARTS


def _list_git_visible_files(*, repo_root: Path) -> tuple[Path, ...]:
    completed_process = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--full-name"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed_process.returncode != 0:
        stderr = completed_process.stderr.strip()
        stdout = completed_process.stdout.strip()
        details = stderr or stdout or "unknown error"
        raise RuntimeError(f"Failed to enumerate repository files for {repo_root}: {details}")

    visible_files: list[Path] = []
    seen_paths: set[Path] = set()
    for raw_line in completed_process.stdout.splitlines():
        normalized_line = raw_line.strip()
        if normalized_line == "":
            continue
        relative_path = Path(normalized_line)
        if relative_path in seen_paths:
            continue
        seen_paths.add(relative_path)
        visible_files.append(relative_path)
    return tuple(sorted(visible_files, key=lambda path: path.as_posix()))


def _should_include_python_context_path(*, relative_path: Path) -> bool:
    if relative_path.suffix != ".py":
        return False
    return not any(part in _EXCLUDED_CONTEXT_PARTS for part in relative_path.parts)


def build_repo_python_context(*, repo_root: Path, separator: str) -> str:
    context_entries = [
        relative_path.as_posix()
        for relative_path in _list_git_visible_files(repo_root=repo_root)
        if _should_include_python_context_path(relative_path=relative_path)
    ]

    if len(context_entries) == 0:
        raise RuntimeError(f"No Python context files found under {repo_root}")

    return separator.join(context_entries)
