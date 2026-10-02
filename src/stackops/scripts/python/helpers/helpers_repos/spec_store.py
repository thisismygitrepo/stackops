import json
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_repos.sync_settings import validate_repo_sync
from stackops.utils.io import save_json
from stackops.utils.schemas.repos.repos_types import GitVersionInfo, RepoRecordDict, RepoRecordFile, RepoRemote, RepoSync
from stackops.utils.source_of_truth import DOTFILES_STACKOPS_ROOT


DEFAULT_REPOS_SPEC_PATH = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "repos.json")
REPOS_SPEC_VERSION = "0.2"


class RepoRecordMergeEntry(TypedDict):
    name: str
    path: str
    branch: str
    changedFields: list[str]


class RepoRecordMergeReport(TypedDict):
    added: list[RepoRecordMergeEntry]
    updated: list[RepoRecordMergeEntry]
    unchanged: list[RepoRecordMergeEntry]
    removed: list[RepoRecordMergeEntry]


def resolve_repos_spec_path(specs_path: str | Path | None) -> Path:
    if specs_path is None:
        return DEFAULT_REPOS_SPEC_PATH
    return Path(specs_path).expanduser().absolute().resolve()


def _validate_object_fields(data: object, *, string_fields: set[str], other_fields: set[str], field_path: str, path: Path) -> dict[str, object]:
    if not isinstance(data, dict):
        raise ValueError(f"""Repository specification field {field_path} must be an object: {path}""")
    fields = cast(dict[str, object], data)
    expected_fields = string_fields | other_fields
    missing_fields = expected_fields - fields.keys()
    unexpected_fields = fields.keys() - expected_fields
    if missing_fields:
        raise ValueError(f"""Missing repository fields at {field_path}: {", ".join(sorted(missing_fields))}: {path}""")
    if unexpected_fields:
        raise ValueError(f"""Unexpected repository fields at {field_path}: {", ".join(sorted(unexpected_fields))}: {path}""")
    for field in sorted(string_fields):
        if not isinstance(fields[field], str):
            raise ValueError(f"""Repository specification field {field_path}.{field} must be a string: {path}""")
    return fields


def _validate_repos_spec(data: object, path: Path) -> RepoRecordFile:
    spec = _validate_object_fields(data, string_fields={"version"}, other_fields={"repos"}, field_path="$", path=path)
    if spec["version"] != REPOS_SPEC_VERSION:
        raise ValueError(f"""Repository specification must use format {REPOS_SPEC_VERSION}: {path}""")
    repos = spec["repos"]
    if not isinstance(repos, list):
        raise ValueError(f"""Repository specification field $.repos must be a list: {path}""")
    validated_records: list[RepoRecordDict] = []
    for index, value in enumerate(repos):
        field_path = f"""$.repos[{index}]"""
        record = _validate_object_fields(
            value,
            string_fields={"name", "parentDir", "currentBranch"},
            other_fields={"remotes", "version", "isDirty", "sync"},
            field_path=field_path,
            path=path,
        )
        if not isinstance(record["isDirty"], bool):
            raise ValueError(f"""Repository specification field {field_path}.isDirty must be a boolean: {path}""")
        version_fields = _validate_object_fields(
            record["version"], string_fields={"branch", "commit"}, other_fields=set(), field_path=f"""{field_path}.version""", path=path
        )
        version: GitVersionInfo = {"branch": cast(str, version_fields["branch"]), "commit": cast(str, version_fields["commit"])}
        remotes = record["remotes"]
        if not isinstance(remotes, list):
            raise ValueError(f"""Repository specification field {field_path}.remotes must be a list: {path}""")
        validated_remotes: list[RepoRemote] = []
        for remote_index, remote in enumerate(remotes):
            remote_fields = _validate_object_fields(
                remote, string_fields={"name", "url"}, other_fields=set(), field_path=f"""{field_path}.remotes[{remote_index}]""", path=path
            )
            validated_remotes.append({"name": cast(str, remote_fields["name"]), "url": cast(str, remote_fields["url"])})
        try:
            sync = validate_repo_sync(value=record["sync"])
        except ValueError as error:
            raise ValueError(f"""Invalid repository field {field_path}.sync: {error}: {path}""") from error
        validated_records.append(
            {
                "name": cast(str, record["name"]),
                "parentDir": cast(str, record["parentDir"]),
                "currentBranch": cast(str, record["currentBranch"]),
                "remotes": validated_remotes,
                "version": version,
                "isDirty": record["isDirty"],
                "sync": sync,
            }
        )
    return {"version": REPOS_SPEC_VERSION, "repos": validated_records}


def load_repos_spec(path: Path) -> RepoRecordFile:
    if not path.exists():
        raise FileNotFoundError(f"Repository specification file not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Repository specification path is not a file: {path}")
    return _validate_repos_spec(json.loads(path.read_text(encoding="utf-8")), path=path)


def load_or_create_repos_spec(path: Path) -> RepoRecordFile:
    if not path.exists():
        return {"version": REPOS_SPEC_VERSION, "repos": []}
    return load_repos_spec(path=path)


def save_repos_spec(spec: RepoRecordFile, path: Path) -> Path:
    return save_json(obj=spec, path=path, indent=4)


def repo_record_path(repo_record: RepoRecordDict) -> Path:
    parent_dir = Path(repo_record["parentDir"]).expanduser()
    return parent_dir.joinpath(repo_record["name"]).absolute().resolve()


def load_repository_syncs(specs_path: str | Path | None) -> dict[Path, RepoSync]:
    path = resolve_repos_spec_path(specs_path=specs_path)
    if specs_path is None and not path.exists():
        return {}
    spec = load_repos_spec(path=path)
    return {repo_record_path(record): record["sync"] for record in spec["repos"]}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _repo_merge_entry(repo_record: RepoRecordDict, changed_fields: list[str] | None = None) -> RepoRecordMergeEntry:
    return {
        "name": repo_record["name"],
        "path": repo_record_path(repo_record).as_posix(),
        "branch": repo_record["currentBranch"],
        "changedFields": changed_fields or [],
    }


def _changed_repo_fields(existing_repo: RepoRecordDict, scanned_repo: RepoRecordDict) -> list[str]:
    fields = ("name", "parentDir", "currentBranch", "remotes", "version", "isDirty", "sync")
    return [field for field in fields if existing_repo[field] != scanned_repo[field]]


def merge_repo_records(
    *, existing_repos: list[RepoRecordDict], scanned_repos: list[RepoRecordDict], scanned_root: Path
) -> tuple[list[RepoRecordDict], RepoRecordMergeReport]:
    root = scanned_root.expanduser().absolute().resolve()
    scanned_by_path = {repo_record_path(repo_record).as_posix(): repo_record for repo_record in scanned_repos}

    merged_repos: list[RepoRecordDict] = []
    report: RepoRecordMergeReport = {"added": [], "updated": [], "unchanged": [], "removed": []}

    for existing_repo in existing_repos:
        existing_path = repo_record_path(existing_repo)
        existing_key = existing_path.as_posix()
        if not _is_relative_to(existing_path, root):
            merged_repos.append(existing_repo)
            continue

        scanned_repo = scanned_by_path.pop(existing_key, None)
        if scanned_repo is None:
            report["removed"].append(_repo_merge_entry(existing_repo))
            continue
        if scanned_repo == existing_repo:
            report["unchanged"].append(_repo_merge_entry(scanned_repo))
        else:
            report["updated"].append(_repo_merge_entry(scanned_repo, changed_fields=_changed_repo_fields(existing_repo, scanned_repo)))
        merged_repos.append(scanned_repo)

    for key in sorted(scanned_by_path):
        scanned_repo = scanned_by_path[key]
        report["added"].append(_repo_merge_entry(scanned_repo))
        merged_repos.append(scanned_repo)

    return merged_repos, report
