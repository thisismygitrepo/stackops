import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_repos_edit
from stackops.scripts.python.helpers.helpers_devops.cli_repos import get_app
from stackops.scripts.python.helpers.helpers_repos import spec_store
from stackops.utils.schemas.repos.repos_types import RepoRecordFile


@pytest.fixture
def spec_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "repos.json"
    specification: RepoRecordFile = {
        "version": spec_store.REPOS_SPEC_VERSION,
        "repos": [{
            "name": "repo",
            "parentDir": tmp_path.as_posix(),
            "currentBranch": "main",
            "remotes": [{"name": "origin", "url": "https://example.invalid/repo.git"}],
            "version": {"branch": "main", "commit": "123abc"},
            "isDirty": False,
            "sync": {"mode": "guard", "cloud": "storage", "remotePath": "backups/repo", "ignoreGitignore": False},
        }],
    }
    path.write_text(json.dumps(specification), encoding="utf-8")
    monkeypatch.setattr(spec_store, "DEFAULT_REPOS_SPEC_PATH", path)
    return path


@pytest.fixture
def editor_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def find_editor(command: str) -> str:
        return f"""/mock/{command}"""

    def run_editor(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(cli_repos_edit.shutil, "which", find_editor)
    monkeypatch.setattr(cli_repos_edit.subprocess, "run", run_editor)
    return calls


@pytest.mark.parametrize("command", ["edit", "e"])
def test_edit_and_alias_open_default_specification(command: str, spec_path: Path, editor_calls: list[list[str]]) -> None:
    result = CliRunner().invoke(get_app(), [command])

    assert result.exit_code == 0, result.output
    assert editor_calls == [["/mock/hx", spec_path.as_posix()]]


@pytest.mark.parametrize(("path_option", "editor_option"), [("--specs-path", "--editor"), ("-s", "-e")])
def test_edit_honors_explicit_path_and_editor(
    path_option: str, editor_option: str, spec_path: Path, editor_calls: list[list[str]],
) -> None:
    alternate_path = spec_path.with_name("alternate.json")
    spec_path.rename(alternate_path)

    result = CliRunner().invoke(get_app(), ["edit", path_option, alternate_path.as_posix(), editor_option, "code"])

    assert result.exit_code == 0, result.output
    assert editor_calls == [["/mock/code", "--wait", alternate_path.as_posix()]]


@pytest.mark.parametrize(("directory", "expected_error"), [(False, "Run devops repos register first"), (True, "not a file")])
def test_edit_rejects_missing_file_or_directory(
    directory: bool, expected_error: str, spec_path: Path, editor_calls: list[list[str]],
) -> None:
    spec_path.unlink()
    if directory:
        spec_path.mkdir()

    result = CliRunner().invoke(get_app(), ["edit"])

    assert result.exit_code == 1
    assert expected_error in result.output
    assert editor_calls == []


def test_edit_rejects_missing_editor(spec_path: Path, editor_calls: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable_editor(_command: str) -> None:
        return None

    monkeypatch.setattr(cli_repos_edit.shutil, "which", unavailable_editor)

    result = CliRunner().invoke(get_app(), ["edit", "-s", spec_path.as_posix()])

    assert result.exit_code == 1
    assert "not available on PATH" in result.output
    assert editor_calls == []


@pytest.mark.parametrize(("editor_status", "expected_status"), [(7, 7), (-15, 1)])
def test_edit_propagates_editor_failure(
    editor_status: int, expected_status: int, spec_path: Path, editor_calls: list[list[str]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_editor(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        return subprocess.CompletedProcess(args=args, returncode=editor_status)

    monkeypatch.setattr(cli_repos_edit.subprocess, "run", failed_editor)

    result = CliRunner().invoke(get_app(), ["edit", "-s", spec_path.as_posix()])

    assert result.exit_code == expected_status
    assert f"""Editor exited with status code {editor_status}""" in result.output
    assert editor_calls == []


def test_edit_reports_editor_launch_error(spec_path: Path, editor_calls: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    def inaccessible_editor(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        raise OSError(f"""Cannot launch {args[0]}""")

    monkeypatch.setattr(cli_repos_edit.subprocess, "run", inaccessible_editor)

    result = CliRunner().invoke(get_app(), ["edit", "-s", spec_path.as_posix()])

    assert result.exit_code == 1
    assert "Could not edit repository specification" in result.output
    assert "Cannot launch /mock/hx" in result.output
    assert editor_calls == []


@pytest.mark.parametrize(
    ("original", "replacement"),
    [
        ("{", ""),
        ('"version": "0.2"', '"version": "0.1"'),
        ('"name": "repo", ', ""),
        ('"isDirty": false', '"isDirty": "no"'),
        ('"url": "https://example.invalid/repo.git"', '"url": 1'),
        ('"remotePath": "backups/repo"', '"remotePath": ""'),
    ],
)
def test_edit_rejects_invalid_content_after_editor_exits(
    original: str, replacement: str, spec_path: Path, editor_calls: list[list[str]],
) -> None:
    invalid_content = spec_path.read_text(encoding="utf-8").replace(original, replacement, 1)
    spec_path.write_text(invalid_content, encoding="utf-8")

    result = CliRunner().invoke(get_app(), ["edit"])

    assert result.exit_code == 1
    assert "Invalid repository specification after editing" in result.output
    assert spec_path.as_posix() in result.output
    assert spec_path.read_text(encoding="utf-8") == invalid_content
    assert editor_calls == [["/mock/hx", spec_path.as_posix()]]


def test_edit_allows_repairing_invalid_existing_content(
    spec_path: Path, editor_calls: list[list[str]], monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid_content = spec_path.read_text(encoding="utf-8")
    spec_path.write_text("{broken", encoding="utf-8")

    def repair_specification(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        editor_calls.append(args)
        Path(args[1]).write_text(valid_content, encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(cli_repos_edit.subprocess, "run", repair_specification)

    result = CliRunner().invoke(get_app(), ["edit"])

    assert result.exit_code == 0, result.output
    assert spec_path.read_text(encoding="utf-8") == valid_content
    assert editor_calls == [["/mock/hx", spec_path.as_posix()]]
