from __future__ import annotations

import platform
import sys
from pathlib import Path
from types import ModuleType

import pytest
import rich.console
import typer
from rich.console import Console
from typer.testing import CliRunner

import stackops.scripts.python.helpers.helpers_devops.cli_self as cli_self
import stackops.utils.code as code_utils


def _install_git_clone_module(monkeypatch: pytest.MonkeyPatch, clone_calls: list[tuple[str, str]]) -> None:
    git_module = ModuleType("git")

    class Repo:
        @staticmethod
        def clone_from(url: str, to_path: str) -> None:
            Path(to_path).mkdir(parents=True, exist_ok=True)
            clone_calls.append((url, to_path))

    setattr(git_module, "Repo", Repo)
    monkeypatch.setitem(sys.modules, "git", git_module)


def _install_dev_app_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    assets_module = ModuleType("stackops.scripts.python.helpers.helpers_devops.cli_self_assets")
    ai_app_module = ModuleType("stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app")
    setattr(assets_module, "get_app", lambda: typer.Typer())
    setattr(ai_app_module, "get_app", lambda: typer.Typer())
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_devops.cli_self_assets", assets_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app", ai_app_module)


def test_init_reads_linux_init_script_from_resolved_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script_path = tmp_path.joinpath("init.sh")
    script_path.write_text("echo linux init", encoding="utf-8")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli_self, "get_path_reference_path", lambda **_kwargs: script_path)

    cli_self.init(which="init", run=False)

    captured = capsys.readouterr()

    assert "echo linux init" in captured.out


def test_update_runs_shell_script_and_copies_assets_on_linux(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_path = tmp_path.joinpath("home")
    home_path.joinpath("code", "stackops").mkdir(parents=True)
    scripts: list[str] = []
    copies: list[str] = []

    monkeypatch.setattr(cli_self.Path, "home", classmethod(lambda cls: home_path))
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(code_utils, "run_shell_script", lambda script, **_kwargs: scripts.append(script))
    monkeypatch.setattr(cli_self, "copy_both_assets", lambda: copies.append("copied"))

    cli_self.update(link_public_configs=False)

    assert len(scripts) == 1
    assert "uv tool install --no-cache --upgrade --editable $HOME/code/stackops" in scripts[0]
    assert copies == ["copied"]


def test_install_dev_clones_repo_before_running_uv_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_path = tmp_path.joinpath("home")
    home_path.mkdir()
    clone_calls: list[tuple[str, str]] = []
    scripts: list[str] = []

    _install_git_clone_module(monkeypatch, clone_calls)
    monkeypatch.setattr(cli_self.Path, "home", classmethod(lambda cls: home_path))
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(code_utils, "get_uv_command", lambda *, platform: "uv")
    monkeypatch.setattr(code_utils, "get_shell_script_running_lambda_function", lambda *args, **kwargs: ("uv run helper", "/tmp/helper.sh"))
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", lambda script: scripts.append(script))

    cli_self.install(dev=True)

    expected_repo_path = home_path.joinpath("code", "stackops")

    assert clone_calls == [("https://github.com/thisismygitrepo/stackops.git", str(expected_repo_path))]
    assert len(scripts) == 1
    assert f"cd {str(expected_repo_path)}" in scripts[0]
    assert "uv sync" in scripts[0]
    assert 'uv tool install --upgrade --editable' in scripts[0]


def test_readme_prefers_local_repo_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home_path = tmp_path.joinpath("home")
    repo_root = home_path.joinpath("code", "stackops")
    repo_root.mkdir(parents=True)
    repo_root.joinpath("README.md").write_text("# Local README\nBody line", encoding="utf-8")
    record_console = Console(record=True, width=120)

    monkeypatch.setattr(cli_self.Path, "home", classmethod(lambda cls: home_path))
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)

    cli_self.readme()

    assert "Local README" in record_console.export_text()


def test_build_docker_raises_when_script_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_module = ModuleType("stackops")
    fake_init = tmp_path.joinpath("pkg", "stackops", "__init__.py")
    fake_init.parent.mkdir(parents=True)
    fake_init.write_text("", encoding="utf-8")
    fake_module.__file__ = fake_init.as_posix()
    monkeypatch.setitem(sys.modules, "stackops", fake_module)

    with pytest.raises(typer.Exit) as exc_info:
        cli_self.buid_docker(variant="slim")

    captured = capsys.readouterr()

    assert exc_info.value.exit_code == 1
    assert "Script not found" in captured.out


def test_get_app_hides_dev_commands_without_developer_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_dev_app_modules(monkeypatch)
    monkeypatch.setattr(cli_self, "_developer_repo_root", lambda: None)
    runner = CliRunner()

    result = runner.invoke(cli_self.get_app(), ["--help"])

    assert result.exit_code == 0
    assert " docs " not in result.stdout
    assert "build-docker" not in result.stdout
    assert "workflows" not in result.stdout


def test_get_app_shows_dev_commands_with_developer_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_dev_app_modules(monkeypatch)
    monkeypatch.setattr(cli_self, "_developer_repo_root", lambda: tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli_self.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "docs" in result.stdout
    assert "build-docker" in result.stdout
    assert "workflows" in result.stdout
