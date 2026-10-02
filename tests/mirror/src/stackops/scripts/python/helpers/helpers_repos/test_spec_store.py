import json
from pathlib import Path
from typing import cast

import pytest
from jsonschema.validators import Draft7Validator

import stackops.utils.schemas.repos as repos_assets
from stackops.scripts.python.helpers.helpers_repos.spec_store import load_repos_spec
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.repos.repos_types import RepoRecordFile, RepoSync


@pytest.fixture
def repository_spec() -> RepoRecordFile:
    return {
        "version": "0.2",
        "repos": [
            {
                "name": "example",
                "parentDir": "/tmp/repositories",
                "currentBranch": "main",
                "remotes": [{"name": "origin", "url": "https://example.invalid/example.git"}],
                "version": {"branch": "main", "commit": "abc123"},
                "isDirty": False,
                "sync": {"mode": "git"},
            }
        ],
    }


@pytest.mark.parametrize(
    "sync", ({"mode": "git"}, {"mode": "guard", "cloud": "example-cloud", "remotePath": "repository.zip.gpg", "ignoreGitignore": True})
)
def test_loader_accepts_schema_valid_repository_records(tmp_path: Path, repository_spec: RepoRecordFile, sync: RepoSync) -> None:
    repository_spec["repos"][0]["sync"] = sync
    schema_path = get_path_reference_path(module=repos_assets, path_reference=repos_assets.REPOS_SCHEMA_PATH_REFERENCE)
    schema = cast(dict[str, object], json.loads(schema_path.read_text(encoding="utf-8")))
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(repository_spec)
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(json.dumps(repository_spec), encoding="utf-8")

    assert load_repos_spec(path=spec_path) == repository_spec


@pytest.mark.parametrize(
    ("document", "expected_error"),
    (
        ([], "must be an object"),
        ({}, "Missing repository fields at $"),
        ({"version": 2, "repos": []}, "$.version must be a string"),
        ({"version": "0.1", "repos": []}, "must use format 0.2"),
        ({"version": "0.2", "repos": {}}, "$.repos must be a list"),
        ({"version": "0.2", "repos": [None]}, "$.repos[0] must be an object"),
        ({"version": "0.2", "repos": [], "extra": True}, "Unexpected repository fields at $"),
    ),
)
def test_loader_rejects_invalid_specification_structure(tmp_path: Path, document: object, expected_error: str) -> None:
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError) as error:
        load_repos_spec(path=spec_path)

    assert expected_error in str(error.value)
    assert spec_path.as_posix() in str(error.value)


@pytest.mark.parametrize(
    ("changes", "expected_field"),
    (
        ({"name": 1}, "name"),
        ({"parentDir": None}, "parentDir"),
        ({"currentBranch": False}, "currentBranch"),
        ({"isDirty": 1}, "isDirty"),
        ({"remotes": {}}, "remotes"),
        ({"remotes": [None]}, "remotes[0]"),
        ({"remotes": [{"name": "origin"}]}, "remotes[0]"),
        ({"remotes": [{"name": 1, "url": "https://example.invalid"}]}, "remotes[0].name"),
        ({"remotes": [{"name": "origin", "url": 1}]}, "remotes[0].url"),
        ({"remotes": [{"name": "origin", "url": "https://example.invalid", "extra": True}]}, "remotes[0]"),
        ({"version": []}, "version"),
        ({"version": {"branch": "main"}}, "version"),
        ({"version": {"branch": False, "commit": "abc123"}}, "version.branch"),
        ({"version": {"branch": "main", "commit": None}}, "version.commit"),
        ({"version": {"branch": "main", "commit": "abc123", "extra": True}}, "version"),
        ({"extra": True}, "$.repos[0]"),
        ({"sync": None}, "sync"),
        ({"sync": {"mode": "unknown"}}, "sync"),
        ({"sync": {"mode": "git", "cloud": "example-cloud"}}, "sync"),
        ({"sync": {"mode": "guard", "cloud": "example-cloud"}}, "sync"),
        ({"sync": {"mode": "guard", "cloud": "", "remotePath": "archive", "ignoreGitignore": False}}, "sync"),
        ({"sync": {"mode": "guard", "cloud": "cloud", "remotePath": "", "ignoreGitignore": False}}, "sync"),
        ({"sync": {"mode": "guard", "cloud": "cloud", "remotePath": "archive", "ignoreGitignore": 1}}, "sync"),
        ({"sync": {"mode": "guard", "cloud": "cloud", "remotePath": "archive", "ignoreGitignore": False, "extra": True}}, "sync"),
    ),
)
def test_loader_rejects_invalid_repository_fields(
    tmp_path: Path, repository_spec: RepoRecordFile, changes: dict[str, object], expected_field: str
) -> None:
    record = cast(dict[str, object], repository_spec["repos"][0])
    record.update(changes)
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(json.dumps(repository_spec), encoding="utf-8")

    with pytest.raises(ValueError) as error:
        load_repos_spec(path=spec_path)

    assert expected_field in str(error.value)
    assert spec_path.as_posix() in str(error.value)


@pytest.mark.parametrize("field", ("name", "parentDir", "currentBranch", "remotes", "version", "isDirty", "sync"))
def test_loader_requires_every_repository_field(tmp_path: Path, repository_spec: RepoRecordFile, field: str) -> None:
    record = cast(dict[str, object], repository_spec["repos"][0])
    del record[field]
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(json.dumps(repository_spec), encoding="utf-8")

    with pytest.raises(ValueError) as error:
        load_repos_spec(path=spec_path)

    assert f"""Missing repository fields at $.repos[0]: {field}""" in str(error.value)


@pytest.mark.parametrize("field", ("cloud", "remotePath"))
def test_loader_rejects_whitespace_guard_settings(tmp_path: Path, repository_spec: RepoRecordFile, field: str) -> None:
    sync: dict[str, object] = {"mode": "guard", "cloud": "cloud", "remotePath": "archive", "ignoreGitignore": False}
    sync[field] = "   "
    record = cast(dict[str, object], repository_spec["repos"][0])
    record["sync"] = sync
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(json.dumps(repository_spec), encoding="utf-8")

    with pytest.raises(ValueError, match="non-empty string"):
        load_repos_spec(path=spec_path)


@pytest.mark.parametrize("text", ("{", "// comment\n{}", '{"version": "0.2", /* comment */ "repos": []}'))
def test_loader_requires_strict_json(tmp_path: Path, text: str) -> None:
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(text, encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_repos_spec(path=spec_path)
