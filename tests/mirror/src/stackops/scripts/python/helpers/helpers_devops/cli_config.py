import platform
from pathlib import Path

import pytest
from typer.testing import CliRunner

import stackops.profile.create_helper as create_helper_module
import stackops.scripts.python.helpers.helpers_devops.cli_config as cli_config_module


def test_dump_config_writes_example_virtual_environment_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cloud_defaults: dict[str, str | bool | None] = {
        "cloud": "maincloud",
        "root": "stackops",
        "rel2home": True,
        "pwd": None,
        "key": None,
        "encrypt": False,
        "os_specific": True,
        "zip": False,
        "share": False,
        "overwrite": True,
    }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_config_module, "read_default_cloud_config", lambda: cloud_defaults)

    cli_config_module.dump_config(which="ve")

    output_path = tmp_path / ".ve.example.yaml"
    content = output_path.read_text(encoding="utf-8")
    assert 'cloud: "maincloud"' in content
    assert "rel2home: true" in content
    assert "pwd: null" in content
    assert "overwrite: true" in content


def test_copy_assets_dispatches_requested_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_copy_assets_to_machine(which: str) -> None:
        calls.append(which)

    monkeypatch.setattr(create_helper_module, "copy_assets_to_machine", fake_copy_assets_to_machine)

    cli_config_module.copy_assets(which="all")
    cli_config_module.copy_assets(which="scripts")
    cli_config_module.copy_assets(which="t")

    assert calls == ["scripts", "settings", "scripts", "settings"]


def test_dump_config_reads_linux_init_script_from_resolved_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script_path = tmp_path.joinpath("init.sh")
    script_path.write_text("echo linux init", encoding="utf-8")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(cli_config_module, "get_path_reference_path", lambda **_kwargs: script_path)

    cli_config_module.dump_config(which="init", run=False)

    captured = capsys.readouterr()

    assert "echo linux init" in captured.out


def test_get_app_help_lists_primary_subcommands() -> None:
    runner = CliRunner()

    result = runner.invoke(cli_config_module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "Define and manage configurations" not in result.stdout
    assert "copy-assets" in result.stdout
    assert "dump" in result.stdout
    assert "terminal" in result.stdout
