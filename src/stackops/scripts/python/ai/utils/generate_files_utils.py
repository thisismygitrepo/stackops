from pathlib import Path


def get_python_files(repo_root: Path, exclude_init: bool = False) -> list[str]:
    """Get all Python files relative to repo root."""
    excluded_parts = {".venv", "__pycache__", ".git", "build", "dist", ".ai"}
    excluded_patterns = {"*.egg-info"}

    py_files = list(repo_root.glob("**/*.py"))

    filtered_files = []
    for file_path in py_files:
        relative_path = file_path.relative_to(repo_root)
        path_parts = relative_path.parts

        if any(part in excluded_parts for part in path_parts):
            continue

        if any(file_path.match(f"**/{pattern}/**") for pattern in excluded_patterns):
            continue

        if exclude_init and file_path.name == "__init__.py":
            continue

        filtered_files.append(str(relative_path))

    return sorted(filtered_files)


def get_shell_files(repo_root: Path) -> list[str]:
    """Get all shell script files relative to repo root."""
    excluded_parts = {".venv", "__pycache__", ".git", "build", "dist"}
    excluded_patterns = {"*.egg-info"}

    sh_files = list(repo_root.glob("**/*.sh"))

    filtered_files = []
    for file_path in sh_files:
        relative_path = file_path.relative_to(repo_root)
        path_parts = relative_path.parts

        if any(part in excluded_parts for part in path_parts):
            continue

        if any(file_path.match(f"**/{pattern}/**") for pattern in excluded_patterns):
            continue

        filtered_files.append(str(relative_path))

    return sorted(filtered_files)


def resolve_scan_root(path: Path) -> Path:
    """Resolve a repo path to its git root, or keep a plain workspace directory as-is."""
    from stackops.utils.accessories import get_repo_root

    resolved_path = path.expanduser().resolve(strict=False)
    if not resolved_path.exists():
        raise ValueError(f"Path does not exist: {resolved_path}")
    candidate_path = resolved_path.parent if resolved_path.is_file() else resolved_path
    repo_root = get_repo_root(candidate_path)
    if repo_root is not None:
        return repo_root.resolve(strict=False)
    return candidate_path


def validate_split_options(*, split_every: int | None, split_to: int | None) -> None:
    """Validate split flags so the command has one strict behavior."""
    if split_every is not None and split_to is not None:
        raise ValueError("Use either --split-every or --split-to, not both")
    if split_every is not None and split_every <= 0:
        raise ValueError("--split-every must be greater than 0")
    if split_to is not None and split_to <= 0:
        raise ValueError("--split-to must be greater than 0")


def resolve_output_base(*, repo_root: Path, output_path: str) -> Path:
    """Resolve the output base path and enforce repo-relative writes."""
    output_path_value = Path(output_path)
    if output_path_value.is_absolute():
        raise ValueError("--output-path must be relative to the repo root")

    resolved_repo_root = repo_root.resolve(strict=False)
    resolved_output_base = (resolved_repo_root / output_path_value).resolve(strict=False)
    if not resolved_output_base.is_relative_to(resolved_repo_root):
        raise ValueError("--output-path must stay within the repo root")
    return resolved_output_base


def filter_files_by_name(files: list[str], pattern: str) -> list[str]:
    """Filter files by filename containing the pattern."""
    return [f for f in files if pattern in f]


def filter_files_by_content(repo_root: Path, files: list[str], keyword: str) -> list[str]:
    """Filter files by content containing the keyword."""
    filtered_files = []
    for file_path in files:
        full_path = repo_root / file_path
        try:
            content = full_path.read_text(encoding="utf-8")
            if keyword in content:
                filtered_files.append(file_path)
        except (IOError, UnicodeDecodeError):
            continue
    return filtered_files


def split_files_into_chunks(all_files: list[str], split_every: int | None = None, split_to: int | None = None) -> list[list[str]]:
    """Split files into chunks based on split_every or split_to."""
    if split_every is not None:
        return [all_files[i:i + split_every] for i in range(0, len(all_files), split_every)]
    elif split_to is not None:
        if split_to <= 0:
            return [all_files]
        chunk_size = max(1, len(all_files) // split_to)
        chunks = []
        for i in range(split_to):
            start = i * chunk_size
            end = start + chunk_size if i < split_to - 1 else len(all_files)
            chunks.append(all_files[start:end])
        return chunks
    else:
        return [all_files]
