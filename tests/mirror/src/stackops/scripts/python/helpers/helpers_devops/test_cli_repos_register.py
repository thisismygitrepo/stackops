import json
from pathlib import Path
from typing import Literal

import pytest
from git.repo import Repo
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops.cli_repos import get_app
from stackops.scripts.python.helpers.helpers_repos.spec_store import REPOS_SPEC_VERSION, load_repos_spec
from stackops.utils.schemas.repos.repos_types import RepoRecordFile


def _initialize_repository(repository_path: Path) -> None:
    with Repo.init(repository_path, initial_branch="main") as repository:
        with repository.config_writer() as config:
            config.set_value("user", "name", "Stackops Tests")
            config.set_value("user", "email", "stackops-tests@example.invalid")
        tracked_file = repository_path.joinpath("tracked.txt")
        tracked_file.write_text("initial\n", encoding="utf-8")
        repository.index.add([tracked_file.as_posix()])
        repository.index.commit("initial")


@pytest.mark.parametrize("location", ["root", "nested"])
@pytest.mark.parametrize("git_marker", ["directory", "worktree"])
@pytest.mark.parametrize("existing_spec", [False, True])
def test_register_rejects_invalid_repository_without_changing_specification(
    location: Literal["root", "nested"],
    git_marker: Literal["directory", "worktree"],
    existing_spec: bool,
    tmp_path: Path,
) -> None:
    workspace = tmp_path.joinpath("workspace")
    workspace.mkdir()
    invalid_repository_path = workspace
    if location == "nested":
        _initialize_repository(repository_path=workspace.joinpath("a-valid"))
        invalid_repository_path = workspace.joinpath("z-invalid")
        invalid_repository_path.mkdir()

    marker_path = invalid_repository_path.joinpath(".git")
    if git_marker == "directory":
        marker_path.mkdir()
    else:
        marker_path.write_text(f"""gitdir: {tmp_path.joinpath('missing-git-dir')}\n""", encoding="utf-8")

    specification_path = tmp_path.joinpath("repos.json")
    original_specification: str | None = None
    if existing_spec:
        specification: RepoRecordFile = {
            "version": REPOS_SPEC_VERSION,
            "repos": [
                {
                    "name": invalid_repository_path.name,
                    "parentDir": invalid_repository_path.parent.as_posix(),
                    "currentBranch": "main",
                    "remotes": [],
                    "version": {"branch": "main", "commit": "0" * 40},
                    "isDirty": False,
                    "sync": {"mode": "git"},
                }
            ],
        }
        original_specification = json.dumps(specification, indent=2)
        specification_path.write_text(original_specification, encoding="utf-8")

    result = CliRunner().invoke(
        get_app(), ["register", workspace.as_posix(), "--specs-path", specification_path.as_posix()], terminal_width=200
    )

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert f"""Cannot register {invalid_repository_path}: not a valid Git repository. Check its .git directory or worktree link.""" in result.output
    assert "Traceback" not in result.output
    if original_specification is None:
        assert not specification_path.exists()
    else:
        assert specification_path.read_text(encoding="utf-8") == original_specification


@pytest.mark.parametrize("location", ["root", "nested"])
def test_register_records_valid_repositories(location: Literal["root", "nested"], tmp_path: Path) -> None:
    workspace = tmp_path.joinpath("workspace")
    workspace.mkdir()
    repository_path = workspace if location == "root" else workspace.joinpath("repository")
    _initialize_repository(repository_path=repository_path)
    specification_path = tmp_path.joinpath("repos.json")

    result = CliRunner().invoke(get_app(), ["register", workspace.as_posix(), "--specs-path", specification_path.as_posix()])

    assert result.exit_code == 0, result.output
    specification = load_repos_spec(path=specification_path)
    assert len(specification["repos"]) == 1
    assert specification["repos"][0]["name"] == repository_path.name
    assert specification["repos"][0]["version"]["branch"] == "main"
    assert len(specification["repos"][0]["version"]["commit"]) == 40
