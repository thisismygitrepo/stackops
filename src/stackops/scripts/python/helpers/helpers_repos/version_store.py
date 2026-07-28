import json
from pathlib import Path, PurePosixPath
from typing import cast

from stackops.scripts.python.helpers.helpers_repos.version_constants import VERSIONS_SCHEMA_VERSION
from stackops.scripts.python.helpers.helpers_repos.version_models import (
    DeclaredVersion,
    RemoteBranchSnapshot,
    RemoteSnapshot,
    RepositorySnapshot,
    VersionsFile,
)
from stackops.utils.io import save_json


class VersionStoreError(ValueError):
    pass


def _json_object(value: object, expected_keys: set[str], context: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise VersionStoreError(f"{context} must be a JSON object")
    result = cast(dict[str, object], value)
    actual_keys = set(result)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        raise VersionStoreError(f"{context} has invalid fields; missing={missing}, unexpected={unexpected}")
    return result


def _json_list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise VersionStoreError(f"{context} must be a JSON list")
    return cast(list[object], value)


def _non_empty_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VersionStoreError(f"{context} must be a non-empty string")
    return value


def _commit(value: object, context: str) -> str:
    commit = _non_empty_string(value=value, context=context)
    if len(commit) not in {40, 64} or any(character not in "0123456789abcdef" for character in commit.lower()):
        raise VersionStoreError(f"{context} must be a full hexadecimal Git object ID")
    return commit.lower()


def _remote_branch(value: object, context: str) -> RemoteBranchSnapshot:
    data = _json_object(value=value, expected_keys={"name", "commit"}, context=context)
    return {
        "name": _non_empty_string(value=data["name"], context=f"{context}.name"),
        "commit": _commit(value=data["commit"], context=f"{context}.commit"),
    }


def _remote(value: object, context: str) -> RemoteSnapshot:
    data = _json_object(value=value, expected_keys={"name", "urls", "branches"}, context=context)
    urls = [
        _non_empty_string(value=url, context=f"{context}.urls[{index}]")
        for index, url in enumerate(_json_list(value=data["urls"], context=f"{context}.urls"))
    ]
    if not urls or urls != sorted(set(urls)):
        raise VersionStoreError(f"{context}.urls must contain sorted, unique remote URLs")
    branches = [
        _remote_branch(value=branch, context=f"{context}.branches[{index}]")
        for index, branch in enumerate(_json_list(value=data["branches"], context=f"{context}.branches"))
    ]
    branch_names = [branch["name"] for branch in branches]
    if branch_names != sorted(set(branch_names)):
        raise VersionStoreError(f"{context}.branches must be sorted by unique branch name")
    return {"name": _non_empty_string(value=data["name"], context=f"{context}.name"), "urls": urls, "branches": branches}


def _repository(value: object, context: str) -> RepositorySnapshot:
    data = _json_object(value=value, expected_keys={"path", "branch", "commit", "isDirty", "remotes"}, context=context)
    path = _non_empty_string(value=data["path"], context=f"{context}.path")
    parsed_path = PurePosixPath(path)
    if parsed_path.is_absolute() or ".." in parsed_path.parts:
        raise VersionStoreError(f"{context}.path must stay within the versions.json directory")
    branch_value = data["branch"]
    if branch_value is not None and (not isinstance(branch_value, str) or not branch_value.strip()):
        raise VersionStoreError(f"{context}.branch must be null or a non-empty string")
    dirty_value = data["isDirty"]
    if not isinstance(dirty_value, bool):
        raise VersionStoreError(f"{context}.isDirty must be a boolean")
    remotes = [
        _remote(value=remote, context=f"{context}.remotes[{index}]")
        for index, remote in enumerate(_json_list(value=data["remotes"], context=f"{context}.remotes"))
    ]
    remote_names = [remote["name"] for remote in remotes]
    if remote_names != sorted(set(remote_names)):
        raise VersionStoreError(f"{context}.remotes must be sorted by unique remote name")
    return {
        "path": parsed_path.as_posix(),
        "branch": branch_value,
        "commit": _commit(value=data["commit"], context=f"{context}.commit"),
        "isDirty": dirty_value,
        "remotes": remotes,
    }


def _declared_version(value: object, context: str) -> DeclaredVersion:
    data = _json_object(value=value, expected_keys={"version", "message", "repositories"}, context=context)
    repositories = [
        _repository(value=repository, context=f"{context}.repositories[{index}]")
        for index, repository in enumerate(_json_list(value=data["repositories"], context=f"{context}.repositories"))
    ]
    paths = [repository["path"] for repository in repositories]
    if not repositories or paths != sorted(set(paths)):
        raise VersionStoreError(f"{context}.repositories must contain sorted, unique repository paths")
    return {
        "version": _non_empty_string(value=data["version"], context=f"{context}.version"),
        "message": _non_empty_string(value=data["message"], context=f"{context}.message"),
        "repositories": repositories,
    }


def _versions_file(value: object, context: str) -> VersionsFile:
    data = _json_object(value=value, expected_keys={"schemaVersion", "versions"}, context=context)
    if data["schemaVersion"] != VERSIONS_SCHEMA_VERSION:
        raise VersionStoreError(f"{context}.schemaVersion must be {VERSIONS_SCHEMA_VERSION!r}, got {data['schemaVersion']!r}")
    versions = [
        _declared_version(value=version, context=f"{context}.versions[{index}]")
        for index, version in enumerate(_json_list(value=data["versions"], context=f"{context}.versions"))
    ]
    names = [version["version"] for version in versions]
    if len(names) != len(set(names)):
        raise VersionStoreError(f"{context}.versions contains duplicate version identifiers")
    return {"schemaVersion": VERSIONS_SCHEMA_VERSION, "versions": versions}


def empty_versions_file() -> VersionsFile:
    return {"schemaVersion": VERSIONS_SCHEMA_VERSION, "versions": []}


def load_versions_file(path: Path, allow_missing: bool) -> VersionsFile:
    if not path.exists():
        if allow_missing:
            return empty_versions_file()
        raise VersionStoreError(f"Versions file not found: {path}")
    if not path.is_file():
        raise VersionStoreError(f"Versions path is not a file: {path}")
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VersionStoreError(f"Failed to read versions file {path}: {error}") from error
    return _versions_file(value=payload, context=str(path))


def save_versions_file(versions_file: VersionsFile, path: Path) -> Path:
    try:
        validated_file = _versions_file(value=versions_file, context=str(path))
        return save_json(obj=validated_file, path=path, indent=4)
    except OSError as error:
        raise VersionStoreError(f"Failed to save versions file {path}: {error}") from error


def find_declared_version(versions_file: VersionsFile, version: str) -> DeclaredVersion:
    for declared_version in versions_file["versions"]:
        if declared_version["version"] == version:
            return declared_version
    raise VersionStoreError(f"Version {version!r} is not declared")


def append_declared_version(versions_file: VersionsFile, declared_version: DeclaredVersion) -> VersionsFile:
    version = declared_version["version"]
    if any(existing["version"] == version for existing in versions_file["versions"]):
        raise VersionStoreError(f"Version {version!r} is already declared")
    return {"schemaVersion": VERSIONS_SCHEMA_VERSION, "versions": [*versions_file["versions"], declared_version]}
