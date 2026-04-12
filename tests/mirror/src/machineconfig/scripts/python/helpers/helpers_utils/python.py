from __future__ import annotations

import json
import platform
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from machineconfig.scripts.python.helpers.helpers_utils import python as module


def _install_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attrs: dict[str, object]) -> None:
    fake_module = ModuleType(module_name)
    for attr_name, attr_value in attrs.items():
        setattr(fake_module, attr_name, attr_value)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_build_env_selection_data_sorts_labels_and_keeps_raw_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module.os, "environ", {"BETA": "second", "ALPHA": ""})

    build_env_selection_data = getattr(module, "_build_env_selection_data")
    previews, outputs = cast(Callable[[], tuple[dict[str, str], dict[str, str]]], build_env_selection_data)()

    assert list(previews) == ["ALPHA = <empty>", "BETA = second"]
    assert previews["ALPHA = <empty>"] == "ALPHA\n\n<empty>"
    assert outputs["BETA = second"] == "second"


def test_choose_with_tv_returns_selected_value(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_module(
        monkeypatch, "machineconfig.utils.installer_utils.installer_locator_utils", {"check_tool_exists": lambda tool_name: tool_name == "tv"}
    )
    _install_module(monkeypatch, "machineconfig.utils.options_utils.tv_options", {"choose_from_dict_with_preview": lambda **_: "KEY = value"})
    monkeypatch.setattr(module, "_build_env_selection_data", lambda: ({"KEY = value": "preview"}, {"KEY = value": "value"}))

    choose_with_tv = getattr(module, "_choose_with_tv")
    used_tv, selected_value = cast(Callable[[str], tuple[bool, str | None]], choose_with_tv)("ENV")

    assert used_tv is True
    assert selected_value == "value"


def test_tui_env_falls_back_to_textual_when_tv_unavailable(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls: list[str] = []

    monkeypatch.setattr(module, "_choose_with_tv", lambda which: (False, None))
    monkeypatch.setattr(module, "_run_textual_env", lambda which: calls.append(which))

    module.tui_env(which="ENV", tui=False)

    captured = capsys.readouterr()
    assert "tv picker unavailable" in captured.err
    assert calls == ["ENV"]


def test_init_project_requires_pyproject_when_not_tmp_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(module.typer.Exit) as excinfo:
        module.init_project(name=None, tmp_dir=False, python="3.13", libraries=None, group="l")

    captured = capsys.readouterr()
    assert excinfo.value.exit_code == 1
    assert "pyproject.toml not found" in captured.err


def test_edit_file_with_hx_builds_repo_aware_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    target_file = repo_root.joinpath("pkg", "demo.py")
    target_file.parent.mkdir(parents=True)
    target_file.write_text("print('demo')\n", encoding="utf-8")

    commands: list[str] = []

    _install_module(monkeypatch, "machineconfig.utils.accessories", {"get_repo_root": lambda root_path: repo_root})
    _install_module(monkeypatch, "machineconfig.utils.code", {"exit_then_run_shell_script": lambda script: commands.append(script)})

    module.edit_file_with_hx(path=str(target_file))

    assert len(commands) == 1
    command = commands[0]
    assert f"cd {repo_root}" in command
    assert "source ./.venv/bin/activate" in command
    assert f"hx {target_file.resolve()}" in command


def test_get_machine_specs_writes_machine_specs_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_root = tmp_path.joinpath("config")

    _install_module(monkeypatch, "machineconfig.utils.code", {"get_uv_command": lambda platform: "uv"})
    _install_module(monkeypatch, "machineconfig.utils.source_of_truth", {"CONFIG_ROOT": config_root})
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "release", lambda: "6.1.0")
    monkeypatch.setattr(platform, "version", lambda: "#1 test")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(platform, "processor", lambda: "Unit Test CPU")
    monkeypatch.setattr(platform, "python_version", lambda: "3.14.0")
    monkeypatch.setattr(socket, "gethostname", lambda: "test-host")
    monkeypatch.setenv("USER", "alex")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout="Test Linux\n", returncode=0))

    specs = module.get_machine_specs(hardware=False)

    written_path = config_root.joinpath("machine_specs.json")
    written_specs = json.loads(written_path.read_text(encoding="utf-8"))
    assert specs["system"] == "Linux"
    assert specs["distro"] == "Test Linux"
    assert specs["hostname"] == "test-host"
    assert specs["processor"] == "Unit Test CPU"
    assert written_specs["python_version"] == "3.14.0"
    assert written_specs["user"] == "alex"
