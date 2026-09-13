from datetime import date
from pathlib import Path
from typing import Literal, NoReturn

import git
import pytest
import typer
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_self, cli_self_release, cli_self_repo, stackops_publish
from stackops.scripts.python.helpers.helpers_devops.stackops_publish import StackOpsPublication
from stackops.scripts.python.helpers.helpers_devops.stackops_release import StackOpsRelease


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    with git.Repo.init(tmp_path):
        pass
    tmp_path.joinpath("pyproject.toml").write_text(
        '''[project]
name = "stackops"
version = "26.9.2"
''',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_self_repo, "STACKOPS_REPO_DIR", tmp_path)
    monkeypatch.setattr(cli_self_release, "STACKOPS_REPO_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize("kind", ["missing", "directory", "checkout"])
def test_release_registration_requires_developer_git_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: Literal["missing", "directory", "checkout"]
) -> None:
    repo_root = tmp_path / "code" / "stackops"
    monkeypatch.setattr(cli_self_repo, "STACKOPS_REPO_DIR", repo_root)
    if kind != "missing":
        repo_root.mkdir(parents=True)
        repo_root.joinpath("pyproject.toml").write_text('[project]\nname = "stackops"\nversion = "26.9.2"\n', encoding="utf-8")
    if kind == "checkout":
        with git.Repo.init(repo_root):
            pass

    result = CliRunner().invoke(cli_self.get_app(), ["release", "--help"])

    if kind == "checkout":
        assert result.exit_code == 0, result.output
        assert "--publish" in result.output
        assert "~/code/stackops" in result.output
    else:
        assert result.exit_code == 2, result.output
        assert "No such command 'release'" in result.output


def test_local_release_uses_fixed_checkout_without_publishing(checkout: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    invocation_roots: list[Path] = []
    elsewhere = checkout / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    def bump(repo_root: Path, today: date) -> StackOpsRelease:
        invocation_roots.append(repo_root)
        assert today == date.today()
        return StackOpsRelease(previous_version="26.9.2", version="26.9.3", changed_files=(Path("pyproject.toml"),))

    def reject_publication(repo_root: Path, today: date) -> NoReturn:
        raise AssertionError(f"""Local release must not prepare publication from {repo_root} on {today}.""")

    monkeypatch.setattr(cli_self_release, "bump_stackops_version", bump)
    monkeypatch.setattr(stackops_publish, "prepare_stackops_publication", reject_publication)

    result = CliRunner().invoke(cli_self.get_app(), ["release"])

    assert result.exit_code == 0, result.output
    assert invocation_roots == [checkout]
    assert "26.9.2 → 26.9.3" in result.output
    assert "ready for review" in result.output


def test_publish_preflights_before_bump_and_reports_tag(checkout: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    prepared_publication = StackOpsPublication(repository="thisismygitrepo/stackops", parent_commit="abc123")
    prepared_release = StackOpsRelease(previous_version="26.9.2", version="26.9.3", changed_files=(Path("pyproject.toml"),))
    release_tag = "v26.9.3"

    def prepare(repo_root: Path, today: date) -> StackOpsPublication:
        assert repo_root == checkout
        assert today == date.today()
        events.append("preflight")
        return prepared_publication

    def bump(repo_root: Path, today: date) -> StackOpsRelease:
        assert repo_root == checkout
        assert today == date.today()
        events.append("bump")
        return prepared_release

    def publish(repo_root: Path, release: StackOpsRelease, publication: StackOpsPublication) -> str:
        assert repo_root == checkout
        assert release == prepared_release
        assert publication == prepared_publication
        events.append("publish")
        return release_tag

    monkeypatch.setattr(stackops_publish, "prepare_stackops_publication", prepare)
    monkeypatch.setattr(cli_self_release, "bump_stackops_version", bump)
    monkeypatch.setattr(stackops_publish, "publish_stackops_release", publish)

    result = CliRunner().invoke(cli_self.get_app(), ["release", "--publish"])

    assert result.exit_code == 0, result.output
    assert events == ["preflight", "bump", "publish"]
    assert f"Pushed {release_tag} and main" in result.output


def test_failed_preflight_does_not_bump(checkout: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_dirty_repo(repo_root: Path, today: date) -> NoReturn:
        assert repo_root == checkout
        assert today == date.today()
        raise RuntimeError("Commit local changes before publishing.")

    def reject_bump(repo_root: Path, today: date) -> NoReturn:
        raise AssertionError(f"""Must not bump {repo_root} on {today} after preflight fails.""")

    monkeypatch.setattr(stackops_publish, "prepare_stackops_publication", reject_dirty_repo)
    monkeypatch.setattr(cli_self_release, "bump_stackops_version", reject_bump)

    result = CliRunner().invoke(cli_self.get_app(), ["release", "--publish"])

    assert result.exit_code == 1, result.output
    assert "Commit local changes before publishing" in result.output


def test_direct_release_rechecks_missing_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_self_release, "STACKOPS_REPO_DIR", tmp_path / "missing")

    with pytest.raises(typer.Exit) as error:
        cli_self_release.release(publish=False)

    assert error.value.exit_code == 1
