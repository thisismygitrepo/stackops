from pathlib import Path
from typing import Any, cast

from stackops.utils.files.read import read_json
from stackops.utils.io import save_json
from stackops.utils.schemas.repos.repos_types import RepoRecordDict, RepoRecordFile


DEFAULT_REPOS_SPEC_PATH = Path("/home/alex/dotfiles/stackops/mapper/repos.json")
REPOS_SPEC_VERSION = "0.1"


def resolve_repos_spec_path(specs_path: str | Path | None = None) -> Path:
    if specs_path is None:
        return DEFAULT_REPOS_SPEC_PATH
    return Path(specs_path).expanduser().absolute().resolve()


def _validate_repos_spec(data: Any, path: Path) -> RepoRecordFile:
    if not isinstance(data, dict):
        raise ValueError(f"Repository specification must be a JSON object: {path}")
    if not isinstance(data.get("version"), str):
        raise ValueError(f"Repository specification is missing string field 'version': {path}")
    if not isinstance(data.get("repos"), list):
        raise ValueError(f"Repository specification is missing list field 'repos': {path}")
    return cast(RepoRecordFile, data)


def load_repos_spec(path: Path) -> RepoRecordFile:
    if not path.exists():
        raise FileNotFoundError(f"Repository specification file not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Repository specification path is not a file: {path}")
    return _validate_repos_spec(read_json(path=path), path=path)


def load_or_create_repos_spec(path: Path) -> RepoRecordFile:
    if not path.exists():
        return {"version": REPOS_SPEC_VERSION, "repos": []}
    return load_repos_spec(path=path)


def save_repos_spec(spec: RepoRecordFile, path: Path) -> Path:
    return save_json(obj=spec, path=path, indent=4)


def repo_record_path(repo_record: RepoRecordDict) -> Path:
    parent_dir = Path(repo_record["parentDir"]).expanduser()
    return parent_dir.joinpath(repo_record["name"]).absolute().resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def merge_repo_records(
    *, existing_repos: list[RepoRecordDict], scanned_repos: list[RepoRecordDict], scanned_root: Path
) -> tuple[list[RepoRecordDict], dict[str, int]]:
    root = scanned_root.expanduser().absolute().resolve()
    scanned_by_path = {repo_record_path(repo_record).as_posix(): repo_record for repo_record in scanned_repos}

    merged_repos: list[RepoRecordDict] = []
    summary = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0}

    for existing_repo in existing_repos:
        existing_path = repo_record_path(existing_repo)
        existing_key = existing_path.as_posix()
        if not _is_relative_to(existing_path, root):
            merged_repos.append(existing_repo)
            continue

        scanned_repo = scanned_by_path.pop(existing_key, None)
        if scanned_repo is None:
            summary["removed"] += 1
            continue
        if scanned_repo == existing_repo:
            summary["unchanged"] += 1
        else:
            summary["updated"] += 1
        merged_repos.append(scanned_repo)

    for key in sorted(scanned_by_path):
        summary["added"] += 1
        merged_repos.append(scanned_by_path[key])

    return merged_repos, summary
