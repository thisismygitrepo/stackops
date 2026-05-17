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


def test_execute_relative_python_file_uses_resolved_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    direct_script = tmp_path.joinpath("tools", "hello.py")
    direct_script.parent.mkdir()
    direct_script.write_text("print('hello')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    captured_python_files: list[str] = []
    executed_scripts: list[str] = []

    def fake_get_uv_command_executing_python_file(
        *,
        python_file: str,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        prepend_print: bool,
    ) -> str:
        _ = uv_with, uv_project_dir, prepend_print
        captured_python_files.append(python_file)
        return "echo direct-python"

    def fake_exit_then_run_shell_script(*, script: str, strict: bool = False) -> None:
        _ = strict
        executed_scripts.append(script)

    monkeypatch.setattr("stackops.utils.code.get_uv_command_executing_python_file", fake_get_uv_command_executing_python_file)
    monkeypatch.setattr("stackops.utils.code.exit_then_run_shell_script", fake_exit_then_run_shell_script)

    result = CliRunner().invoke(devops_app.get_app(), ["execute", "tools/hello.py"])

    assert result.exit_code == 0
    assert captured_python_files == [str(direct_script.resolve())]
    assert executed_scripts == ["echo direct-python"]
