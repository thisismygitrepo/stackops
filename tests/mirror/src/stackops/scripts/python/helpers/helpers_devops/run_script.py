from pathlib import Path

import pytest
from typer.testing import CliRunner

import stackops.scripts.python.devops as devops_app


def test_execute_command_requires_non_empty_command() -> None:
    result = CliRunner().invoke(devops_app.get_app(), ["execute", "--command"])

    assert result.exit_code == 1
    assert "You must provide a command to run when using --command." in result.stdout


def test_execute_requires_interactive_for_ambiguous_matches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_scripts = tmp_path.joinpath("scripts")
    repo_scripts.mkdir()
    repo_scripts.joinpath("build_api.sh").write_text("echo api\n", encoding="utf-8")
    repo_scripts.joinpath("build_web.sh").write_text("echo web\n", encoding="utf-8")

    monkeypatch.setattr("stackops.utils.repo_stackops.require_current_repo_stackops_path", lambda *, path_kind: repo_scripts)

    result = CliRunner().invoke(devops_app.get_app(), ["execute", "build", "--where", "repo"])

    assert result.exit_code == 1
    assert "Found 2 scripts matching 'build'." in result.stdout
    assert "Re-run with --interactive to choose one explicitly." in result.stdout
    assert str(repo_scripts.joinpath("build_api.sh")) in result.stdout
    assert str(repo_scripts.joinpath("build_web.sh")) in result.stdout


def test_execute_uses_selector_for_ambiguous_matches_when_interactive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_scripts = tmp_path.joinpath("scripts")
    repo_scripts.mkdir()
    selected_script = repo_scripts.joinpath("build_api.sh")
    repo_scripts.joinpath("build_web.sh").write_text("echo web\n", encoding="utf-8")
    selected_script.write_text("echo api\n", encoding="utf-8")

    captured_options: list[list[str]] = []
    executed_scripts: list[str] = []

    monkeypatch.setattr("stackops.utils.repo_stackops.require_current_repo_stackops_path", lambda *, path_kind: repo_scripts)

    def fake_choose_from_options(
        options: list[str],
        *,
        multi: bool,
        msg: str,
        tv: bool,
        preview: str,
    ) -> str:
        _ = multi, msg, tv, preview
        captured_options.append(options)
        return str(selected_script)

    def fake_exit_then_run_shell_file(*, script_path: str, strict: bool) -> None:
        _ = strict
        executed_scripts.append(script_path)

    monkeypatch.setattr("stackops.utils.options.choose_from_options", fake_choose_from_options)
    monkeypatch.setattr("stackops.utils.code.exit_then_run_shell_file", fake_exit_then_run_shell_file)

    result = CliRunner().invoke(devops_app.get_app(), ["execute", "build", "--where", "repo", "--interactive"])

    assert result.exit_code == 0
    assert captured_options == [[str(selected_script), str(repo_scripts.joinpath("build_web.sh"))]]
    assert executed_scripts == [str(selected_script)]
