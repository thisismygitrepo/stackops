from __future__ import annotations

import sys
from types import ModuleType

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_devops import cli_share_file as module


def install_address_helper(monkeypatch: pytest.MonkeyPatch, lan_ip: str | None) -> None:
    import machineconfig.scripts.python.helpers as helpers_package

    helpers_network_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network")
    address_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network.address")

    def fake_select_lan_ipv4(*, prefer_vpn: bool) -> str | None:
        assert prefer_vpn is False
        return lan_ip

    setattr(address_module, "select_lan_ipv4", fake_select_lan_ipv4)
    setattr(helpers_network_module, "address", address_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network", helpers_network_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network.address", address_module)
    monkeypatch.setattr(helpers_package, "helpers_network", helpers_network_module, raising=False)


def test_share_file_receive_parses_sys_argv_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    recorded_scripts: list[str] = []
    recorded_lexers: list[str] = []
    code_module = ModuleType("machineconfig.utils.code")

    def fake_print_code(*, code: str, desc: str, lexer: str) -> None:
        assert desc == "🚀 Receiving file with croc"
        recorded_scripts.append(code)
        recorded_lexers.append(lexer)

    def fake_exit_then_run_shell_script(*, script: str, strict: bool) -> None:
        assert strict is False
        recorded_scripts.append(script)

    setattr(code_module, "print_code", fake_print_code)
    setattr(code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.code", code_module)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(sys, "argv", ["devops", "network", "receive", "--", "croc", "--relay", "10.17.62.206:443", "7121-donor-olympic-bicycle"])

    module.share_file_receive(code_args=[], install_missing_dependencies=False)

    expected_script = """export CROC_SECRET=\"7121-donor-olympic-bicycle\"
croc --relay 10.17.62.206:443 --yes"""
    assert recorded_scripts == [expected_script, expected_script]
    assert recorded_lexers == ["bash"]


def test_share_file_receive_exits_when_input_cannot_be_parsed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as exc_info:
        module.share_file_receive(code_args=["plainword"], install_missing_dependencies=False)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "Could not parse croc receive code" in captured.err


def test_share_file_send_builds_wormhole_command(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import platform

    recorded_scripts: list[str] = []
    code_module = ModuleType("machineconfig.utils.code")

    def fake_print_code(*, code: str, desc: str, lexer: str) -> None:
        assert desc == "🚀 sending file with croc"
        assert lexer == "bash"
        recorded_scripts.append(code)

    def fake_exit_then_run_shell_script(*, script: str, strict: bool) -> None:
        assert strict is False
        recorded_scripts.append(script)

    setattr(code_module, "print_code", fake_print_code)
    setattr(code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.code", code_module)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    module.share_file_send(
        path="/tmp/report.txt",
        zip_folder=False,
        code="alpha-beta",
        text="payload text",
        qrcode=False,
        backend="wormhole",
        install_missing_dependencies=False,
    )

    expected_script = """
uvx magic-wormhole send --code alpha-beta --text 'payload text'
"""
    assert recorded_scripts == [expected_script, expected_script]
    assert "Use: devops network receive" in capsys.readouterr().out


def test_share_file_send_croc_requires_lan_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    install_address_helper(monkeypatch, None)

    with pytest.raises(typer.Exit) as exc_info:
        module.share_file_send(
            path="/tmp/report.txt", zip_folder=False, code=None, text=None, qrcode=False, backend="croc", install_missing_dependencies=False
        )

    assert exc_info.value.exit_code == 1
