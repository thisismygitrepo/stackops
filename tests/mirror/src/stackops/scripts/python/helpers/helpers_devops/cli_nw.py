

import sys
from types import ModuleType

import pytest
import rich
import rich.console
from rich.console import Console
from typer.testing import CliRunner

import stackops.scripts.python.helpers.helpers_devops.cli_nw as cli_nw
import stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share as cli_nw_vscode_share
import stackops.utils.code as code_utils


def _install_address_helper(
    monkeypatch: pytest.MonkeyPatch,
    *,
    public_ip: dict[str, str] | Exception,
    addresses: list[tuple[str, str]],
    selected_lan_ip: str | None,
) -> None:
    package_module = ModuleType("stackops.scripts.python.helpers.helpers_network")
    helper_module = ModuleType("stackops.scripts.python.helpers.helpers_network.address")

    def get_public_ip_address() -> dict[str, str]:
        if isinstance(public_ip, Exception):
            raise public_ip
        return public_ip

    def get_all_ipv4_addresses() -> list[tuple[str, str]]:
        return addresses.copy()

    def select_lan_ipv4(*, prefer_vpn: bool) -> str | None:
        assert prefer_vpn is False
        return selected_lan_ip

    setattr(helper_module, "get_public_ip_address", get_public_ip_address)
    setattr(helper_module, "get_all_ipv4_addresses", get_all_ipv4_addresses)
    setattr(helper_module, "select_lan_ipv4", select_lan_ipv4)
    setattr(package_module, "address", helper_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_network", package_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_network.address", helper_module)


def test_show_address_prints_public_and_selected_lan_ip(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_calls: list[dict[str, str]] = []
    record_console = Console(record=True, width=120)
    _install_address_helper(
        monkeypatch,
        public_ip={"ip": "1.2.3.4"},
        addresses=[("eth0", "192.168.1.20")],
        selected_lan_ip="192.168.1.20",
    )
    monkeypatch.setattr(rich, "print_json", lambda *, data: json_calls.append(data))
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)

    cli_nw.show_address()

    captured = capsys.readouterr()

    assert json_calls == [{"ip": "1.2.3.4"}]
    assert "LAN IPv4: 192.168.1.20" in captured.out
    assert "Network Interfaces" in record_console.export_text()


def test_show_address_handles_public_ip_lookup_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    record_console = Console(record=True, width=120)
    _install_address_helper(
        monkeypatch,
        public_ip=RuntimeError("boom"),
        addresses=[],
        selected_lan_ip=None,
    )
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)

    cli_nw.show_address()

    captured = capsys.readouterr()

    assert "Could not fetch public IP address: boom" in captured.out
    assert "No network interfaces found." in captured.out


def test_vscode_share_share_local_builds_and_runs_serve_web_command(monkeypatch: pytest.MonkeyPatch) -> None:
    printed_commands: list[str] = []
    executed_commands: list[str] = []
    shared_urls: list[tuple[str, str | None]] = []

    monkeypatch.setattr(cli_nw_vscode_share, "resolve_share_local_folder", lambda directory: "/tmp/workspace")
    monkeypatch.setattr(
        cli_nw_vscode_share,
        "ensure_without_connection_token",
        lambda extra_args: "--without-connection-token --telemetry-level off",
    )
    monkeypatch.setattr(
        cli_nw_vscode_share,
        "print_serve_web_urls",
        lambda cmd, *, folder_path: shared_urls.append((cmd, folder_path)),
    )
    monkeypatch.setattr(code_utils, "print_code", lambda code, **_kwargs: printed_commands.append(code))
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", lambda code: executed_commands.append(code))

    cli_nw.vscode_share(
        action="share-local",
        name=None,
        path="base",
        host="0.0.0.0",
        directory=".",
        extra_args="--telemetry-level off",
    )

    expected_command = (
        "code serve-web --accept-server-license-terms --host 0.0.0.0 --server-base-path base "
        "--without-connection-token --telemetry-level off"
    )

    assert printed_commands == [expected_command]
    assert executed_commands == [expected_command]
    assert shared_urls == [(expected_command, "/tmp/workspace")]


def test_get_app_help_lists_vscode_share_command() -> None:
    runner = CliRunner()

    result = runner.invoke(cli_nw.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "vscode-share" in result.stdout
    assert "show-address" in result.stdout
