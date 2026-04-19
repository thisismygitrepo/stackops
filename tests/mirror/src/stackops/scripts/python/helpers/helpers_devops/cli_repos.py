

import sys
from pathlib import Path
from types import ModuleType

import pytest
import typer

import stackops.scripts.python.helpers.helpers_devops.cli_repos as cli_repos
import stackops.utils.code as code_utils


def _install_git_module(monkeypatch: pytest.MonkeyPatch, *, raise_on_repo: bool) -> None:
    git_module = ModuleType("git")

    class InvalidGitRepositoryError(Exception):
        pass

    class Repo:
        def __init__(self, _path: str, search_parent_directories: bool = False) -> None:
            _ = search_parent_directories
            if raise_on_repo:
                raise InvalidGitRepositoryError("not a repo")

    setattr(git_module, "InvalidGitRepositoryError", InvalidGitRepositoryError)
    setattr(git_module, "Repo", Repo)
    monkeypatch.setitem(sys.modules, "git", git_module)


def test_action_requires_at_least_one_selected_operation(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as exc_info:
        cli_repos.action(directory=None, recursive=False, auto_uv_sync=False, pull=False, commit=False, push=False)

    captured = capsys.readouterr()

    assert exc_info.value.exit_code == 1
    assert "No action selected" in captured.out


def test_clone_with_explicit_specs_path_calls_clone_repos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec_path = tmp_path.joinpath("repos.json")
    spec_path.write_text("[]", encoding="utf-8")
    captured: dict[str, object] = {}
    clone_module = ModuleType("stackops.scripts.python.helpers.helpers_repos.clone")

    def clone_repos(*, spec_path: Path, preferred_remote: str | None, checkout_branch_flag: bool, checkout_commit_flag: bool) -> None:
        captured["spec_path"] = spec_path
        captured["preferred_remote"] = preferred_remote
        captured["checkout_branch_flag"] = checkout_branch_flag
        captured["checkout_commit_flag"] = checkout_commit_flag

    setattr(clone_module, "clone_repos", clone_repos)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_repos.clone", clone_module)

    cli_repos.clone(
        directory=".",
        specs_path=spec_path.as_posix(),
        interactive=False,
        checkout_to_commit=True,
        checkout_to_branch=False,
    )

    assert captured == {
        "spec_path": spec_path.expanduser().absolute(),
        "preferred_remote": None,
        "checkout_branch_flag": False,
        "checkout_commit_flag": True,
    }


def test_clone_reports_missing_default_spec_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_module = ModuleType("stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile")
    setattr(config_module, "get_backup_path", lambda **_kwargs: tmp_path.joinpath("missing.json"))
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile", config_module)
    monkeypatch.setattr(cli_repos, "_resolve_directory", lambda directory: tmp_path)

    cli_repos.clone(
        directory=tmp_path.as_posix(),
        specs_path=None,
        interactive=False,
        checkout_to_commit=False,
        checkout_to_branch=False,
    )

    captured = capsys.readouterr()

    assert "Specification file not found" in captured.out
    assert str(tmp_path.joinpath("missing.json")) in captured.out


def test_cleanup_recursive_runs_cleanpy_for_each_git_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_one = tmp_path.joinpath("repo-one")
    repo_two = tmp_path.joinpath("nested", "repo-two")
    repo_one.joinpath(".git").mkdir(parents=True)
    repo_two.joinpath(".git").mkdir(parents=True)
    scripts: list[str] = []

    _install_git_module(monkeypatch, raise_on_repo=False)
    monkeypatch.setattr(code_utils, "run_shell_script", lambda script, **_kwargs: scripts.append(script))

    cli_repos.cleanup(repo=tmp_path.as_posix(), recursive=True)

    assert len(scripts) == 2
    assert f'cd "{repo_one.absolute()}"' in scripts[0] or f'cd "{repo_one.absolute()}"' in scripts[1]
    assert f'cd "{repo_two.absolute()}"' in scripts[0] or f'cd "{repo_two.absolute()}"' in scripts[1]
    assert all("uv run --with cleanpy cleanpy ." in script for script in scripts)


def test_config_linters_copies_requested_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_git_module(monkeypatch, raise_on_repo=False)

    cli_repos.config_linters(directory=tmp_path.as_posix(), linter="ty")

    destination = tmp_path.joinpath("ty.toml")
    source = Path(cli_repos.__file__).resolve().parents[4].joinpath("settings", "linters", "ty.toml")

    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
