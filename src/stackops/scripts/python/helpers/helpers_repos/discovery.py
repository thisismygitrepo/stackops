import os
from pathlib import Path

from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.repo import Repo


def repository_candidates(repos_root: Path, recursive: bool) -> list[Path]:
    try:
        Repo(repos_root, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError):
        pass
    else:
        return [repos_root]

    if not recursive:
        return sorted(repos_root.glob("*"))

    repository_paths: list[Path] = []
    for current_root, directory_names, file_names in os.walk(repos_root):
        current_path = Path(current_root)
        if ".git" in directory_names or ".git" in file_names:
            repository_paths.append(current_path)
            directory_names.clear()
            continue
        directory_names[:] = [name for name in directory_names if not name.startswith(".")]
    return sorted(repository_paths)
