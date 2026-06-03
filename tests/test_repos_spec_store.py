import json
from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python.devops import get_app
from stackops.scripts.python.helpers.helpers_repos import record as record_module
from stackops.scripts.python.helpers.helpers_repos.spec_store import DEFAULT_REPOS_SPEC_PATH, merge_repo_records, resolve_repos_spec_path
from stackops.utils.schemas.repos.repos_types import RepoRecordDict


def _repo_record(parent_dir: Path, name: str, branch: str = "main") -> RepoRecordDict:
    return {
        "name": name,
        "parentDir": parent_dir.as_posix(),
        "currentBranch": branch,
        "remotes": [{"name": "origin", "url": f"git@example.com:{name}.git"}],
        "version": {"branch": branch, "commit": f"{name}-commit"},
        "isDirty": False,
    }


def test_resolve_repos_spec_path_defaults_to_single_user_spec() -> None:
    assert resolve_repos_spec_path() == DEFAULT_REPOS_SPEC_PATH


def test_merge_repo_records_refreshes_only_scanned_root(tmp_path: Path) -> None:
    code_root = tmp_path / "code"
    other_root = tmp_path / "other"
    code_root.mkdir()
    other_root.mkdir()

    existing_repos = [_repo_record(code_root, "alpha", branch="old"), _repo_record(code_root, "stale"), _repo_record(other_root, "keep")]
    scanned_repos = [_repo_record(code_root, "alpha", branch="new"), _repo_record(code_root, "beta")]

    merged_repos, report = merge_repo_records(existing_repos=existing_repos, scanned_repos=scanned_repos, scanned_root=code_root)

    assert [entry["name"] for entry in report["added"]] == ["beta"]
    assert [entry["name"] for entry in report["updated"]] == ["alpha"]
    assert report["updated"][0]["changedFields"] == ["currentBranch", "version"]
    assert report["unchanged"] == []
    assert [entry["name"] for entry in report["removed"]] == ["stale"]
    assert [(repo["parentDir"], repo["name"], repo["currentBranch"]) for repo in merged_repos] == [
        (code_root.as_posix(), "alpha", "new"),
        (other_root.as_posix(), "keep", "main"),
        (code_root.as_posix(), "beta", "main"),
    ]


def test_record_repos_recursively_records_scan_root_when_it_is_git_repo(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "bithence"
    repo_root.joinpath(".git").mkdir(parents=True)
    repo_root.joinpath("src").mkdir()
    recorded_paths: list[Path] = []

    def fake_record_a_repo(path: Path, search_parent_directories: bool, preferred_remote: str | None) -> RepoRecordDict:
        recorded_paths.append(path)
        assert search_parent_directories is False
        assert preferred_remote is None
        return _repo_record(repo_root.parent, repo_root.name)

    monkeypatch.setattr(record_module, "record_a_repo", fake_record_a_repo)

    assert record_module.count_total_directories(repo_root.as_posix(), r=True) == 0
    assert record_module.count_git_repositories(repo_root.as_posix(), r=True) == 1

    repo_records = record_module.record_repos_recursively(
        repos_root=repo_root.as_posix(), r=True, progress=None, scan_task_id=None, process_task_id=None
    )

    assert recorded_paths == [repo_root.absolute()]
    assert [repo["name"] for repo in repo_records] == ["bithence"]


def test_main_record_updates_current_directory_repo_instead_of_pruning_it(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "bytesense" / "bithence"
    repo_root.joinpath(".git").mkdir(parents=True)
    spec_path = tmp_path / "repos.json"
    spec_path.write_text(json.dumps({"version": "0.1", "repos": [_repo_record(repo_root.parent, repo_root.name, branch="old")]}))

    def fake_record_a_repo(path: Path, search_parent_directories: bool, preferred_remote: str | None) -> RepoRecordDict:
        assert path == repo_root.absolute()
        assert search_parent_directories is False
        assert preferred_remote is None
        return _repo_record(repo_root.parent, repo_root.name, branch="new")

    monkeypatch.setattr(record_module, "record_a_repo", fake_record_a_repo)

    record_module.main_record(repos_root_str=repo_root.as_posix(), specs_path=spec_path)

    saved_spec = json.loads(spec_path.read_text())
    assert [(repo["name"], repo["currentBranch"]) for repo in saved_spec["repos"]] == [("bithence", "new")]


def test_devops_repos_sync_help_uses_global_spec_shape() -> None:
    result = CliRunner().invoke(get_app(), ["repos", "sync", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "--specs-path" in result.output
    assert "--interactive" not in result.output
    assert "DIRECTORY" not in result.output
