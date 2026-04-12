from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_devops import cli_share_server as module


def install_web_file_explorer_stubs(monkeypatch: pytest.MonkeyPatch, lan_ip: str | None, recorded_scripts: list[str]) -> list[str]:
    import machineconfig.scripts.python.helpers as helpers_package

    installer_calls: list[str] = []
    installer_module = ModuleType("machineconfig.utils.installer_utils.installer_cli")
    helpers_network_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network")
    address_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network.address")
    code_module = ModuleType("machineconfig.utils.code")

    def fake_install_if_missing(*, which: str, binary_name: str | None, verbose: bool) -> None:
        assert binary_name is None
        assert verbose is True
        installer_calls.append(which)

    def fake_select_lan_ipv4(*, prefer_vpn: bool) -> str | None:
        assert prefer_vpn is False
        return lan_ip

    def fake_exit_then_run_shell_script(*, script: str, strict: bool) -> None:
        assert strict is False
        recorded_scripts.append(script)

    setattr(installer_module, "install_if_missing", fake_install_if_missing)
    setattr(address_module, "select_lan_ipv4", fake_select_lan_ipv4)
    setattr(helpers_network_module, "address", address_module)
    setattr(code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.installer_utils.installer_cli", installer_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network", helpers_network_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network.address", address_module)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.code", code_module)
    monkeypatch.setattr(helpers_package, "helpers_network", helpers_network_module, raising=False)
    return installer_calls


def test_web_file_explorer_builds_miniserve_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    recorded_scripts: list[str] = []
    displayed_messages: list[tuple[str, str]] = []
    install_web_file_explorer_stubs(monkeypatch, "10.0.0.42", recorded_scripts)

    def fake_display_with_flashy_style(*, msg: str, title: str) -> None:
        displayed_messages.append((msg, title))

    monkeypatch.setattr(module, "display_with_flashy_style", fake_display_with_flashy_style)

    shared_dir = tmp_path.joinpath("shared")
    shared_dir.mkdir()
    module.web_file_explorer(
        path=str(shared_dir),
        port=9000,
        username="alex",
        no_auth=False,
        password="secret",
        bind_address="127.0.0.1",
        over_internet=False,
        backend="miniserve",
        install_missing_dependencies=False,
    )

    assert displayed_messages == [("http://10.0.0.42:9000/", "Local Network Share URL")]
    assert recorded_scripts == [
        f'miniserve --port 9000 --interfaces 127.0.0.1 --auth "alex:secret"  --upload-files --mkdir --enable-tar --enable-tar-gz --enable-zip --qrcode "{shared_dir.resolve()}" '
    ]


def test_web_file_explorer_reads_default_password_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import getpass

    recorded_scripts: list[str] = []
    install_web_file_explorer_stubs(monkeypatch, "10.0.0.7", recorded_scripts)
    monkeypatch.setattr(module, "display_with_flashy_style", lambda *, msg, title: None)
    home_dir = tmp_path.joinpath("home")
    password_file = home_dir.joinpath("dotfiles/creds/passwords/quick_password")
    password_file.parent.mkdir(parents=True)
    password_file.write_text("vault-secret\n", encoding="utf-8")
    monkeypatch.setattr(module.Path, "home", classmethod(lambda cls: home_dir))
    monkeypatch.setattr(getpass, "getuser", lambda: "alex")

    shared_dir = tmp_path.joinpath("shared")
    shared_dir.mkdir()
    module.web_file_explorer(
        path=str(shared_dir),
        port=None,
        username=None,
        no_auth=False,
        password=None,
        bind_address="0.0.0.0",
        over_internet=False,
        backend="miniserve",
        install_missing_dependencies=False,
    )

    assert '--auth "alex:vault-secret"' in recorded_scripts[0]
    assert "--port 8080" in recorded_scripts[0]


def test_web_file_explorer_rejects_invalid_backend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install_web_file_explorer_stubs(monkeypatch, "10.0.0.3", [])

    with pytest.raises(typer.Exit) as exc_info:
        module.web_file_explorer(
            path=str(tmp_path),
            port=8000,
            username=None,
            no_auth=True,
            password=None,
            bind_address="0.0.0.0",
            over_internet=False,
            backend="invalid",
            install_missing_dependencies=False,
        )

    assert exc_info.value.exit_code == 1
    assert "Invalid backend" in capsys.readouterr().err


def test_get_share_file_app_registers_expected_commands() -> None:
    app = module.get_share_file_app()
    command_names = [command_info.name for command_info in app.registered_commands]

    assert command_names == ["send", "s", "receive", "r"]


def test_main_with_parser_uses_typer_run(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded_targets: list[object] = []

    def fake_run(target: object) -> None:
        recorded_targets.append(target)

    monkeypatch.setattr(module.typer, "run", fake_run)

    module.main_with_parser()

    assert recorded_targets == [module.web_file_explorer]
