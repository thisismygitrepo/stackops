import json
from pathlib import Path
import sys
import types
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

import stackops.scripts.python.helpers.helpers_devops as helpers_devops_package
from stackops.scripts.python.helpers.helpers_devops import cli_config

TERMINAL_MODULE_NAME = "stackops.scripts.python.helpers.helpers_devops.cli_config_terminal"


def test_dump_does_not_import_terminal_subapp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_terminal_module = types.ModuleType(TERMINAL_MODULE_NAME)

    def fail_on_attr(name: str) -> object:
        raise AssertionError(f"unexpected terminal module access: {name}")

    setattr(fake_terminal_module, "__getattr__", fail_on_attr)
    monkeypatch.setitem(sys.modules, TERMINAL_MODULE_NAME, fake_terminal_module)
    monkeypatch.setattr(helpers_devops_package, "cli_config_terminal", fake_terminal_module, raising=False)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_config.get_app(), ["dump", "--which", "ve"])

    assert result.exit_code == 0
    assert (tmp_path / ".ve.example.yaml").is_file()


def test_dump_layout_writes_example_and_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_config.get_app(), ["dump", "--which", "layout"])

    assert result.exit_code == 0
    layout_path = tmp_path / "layout.json"
    schema_path = tmp_path / "layout.schema.json"
    assert layout_path.is_file()
    assert schema_path.is_file()
    assert json.loads(layout_path.read_text(encoding="utf-8"))["layouts"][0]["layoutName"] == "g1"
    assert json.loads(schema_path.read_text(encoding="utf-8"))["title"] == "Terminal Layouts Schema"


def test_dump_layout_example_alias_writes_example_and_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_config.get_app(), ["dump", "--which", "layout-example"])

    assert result.exit_code == 0
    assert (tmp_path / "layout.json").is_file()
    assert (tmp_path / "layout.schema.json").is_file()


def test_dump_layout_rejects_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli_config.get_app(), ["dump", "--which", "layout", "--run"])

    assert result.exit_code == 1
    assert "--run is only valid when dumping init scripts." in result.stdout
    assert not (tmp_path / "layout.json").exists()


def test_terminal_subcommand_delegates_to_nested_app(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_terminal_module = types.ModuleType(TERMINAL_MODULE_NAME)

    def get_fake_app() -> typer.Typer:
        terminal_app = typer.Typer()

        @terminal_app.command("ping")
        def ping() -> None:
            typer.echo("pong")

        @terminal_app.command("other")
        def other() -> None:
            typer.echo("other")

        return terminal_app

    setattr(fake_terminal_module, "get_app", get_fake_app)
    monkeypatch.setitem(sys.modules, TERMINAL_MODULE_NAME, fake_terminal_module)
    monkeypatch.setattr(helpers_devops_package, "cli_config_terminal", fake_terminal_module, raising=False)

    result = CliRunner().invoke(cli_config.get_app(), ["terminal", "ping"])

    assert result.exit_code == 0
    assert result.stdout == "pong\n"


def test_dump_config_rejects_unknown_kind() -> None:
    with pytest.raises(typer.Exit) as exit_info:
        cli_config.dump_config(which=cast(cli_config.DumpConfigKind, "broken"), run=False)

    assert exit_info.value.exit_code == 1
