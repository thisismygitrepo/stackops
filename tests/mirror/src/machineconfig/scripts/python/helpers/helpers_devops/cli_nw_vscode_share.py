from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import rich.console
from rich.console import Console

import machineconfig.scripts.python.helpers.helpers_devops.cli_nw_vscode_share as cli_nw_vscode_share


def _install_address_helper(monkeypatch, addresses: list[tuple[str, str]] | Exception) -> None:
    package_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network")
    helper_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network.address")

    def get_all_ipv4_addresses() -> list[tuple[str, str]]:
        if isinstance(addresses, Exception):
            raise addresses
        return addresses

    helper_module.get_all_ipv4_addresses = get_all_ipv4_addresses
    package_module.address = helper_module
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network", package_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network.address", helper_module)


def test_ensure_without_connection_token_adds_flag_only_when_missing() -> None:
    assert cli_nw_vscode_share.ensure_without_connection_token("") == "--without-connection-token"
    assert cli_nw_vscode_share.ensure_without_connection_token("--telemetry-level off") == "--without-connection-token --telemetry-level off"
    assert cli_nw_vscode_share.ensure_without_connection_token("--connection-token abc") == "--connection-token abc"


def test_get_serve_web_details_uses_defaults_and_invalid_port_fallback() -> None:
    assert cli_nw_vscode_share._get_serve_web_details("code serve-web") == ("localhost", 8000, "")
    assert cli_nw_vscode_share._get_serve_web_details("code serve-web --host 0.0.0.0 --port nope --server-base-path /dev") == (
        "0.0.0.0",
        8000,
        "/dev",
    )


def test_resolve_share_local_folder_uses_cwd_and_expands_user(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    cwd_result = cli_nw_vscode_share.resolve_share_local_folder(None)
    explicit_result = cli_nw_vscode_share.resolve_share_local_folder(tmp_path.joinpath("child").as_posix())

    assert cwd_result == str(tmp_path.resolve())
    assert explicit_result == str(tmp_path.joinpath("child").resolve(strict=False))


def test_print_serve_web_urls_lists_all_reachable_urls(monkeypatch) -> None:
    record_console = Console(record=True, width=200)
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)
    monkeypatch.setattr(cli_nw_vscode_share.platform, "node", lambda: "hostbox")
    _install_address_helper(monkeypatch, [("lo", "127.0.0.1"), ("eth0", "192.168.1.5")])

    cli_nw_vscode_share.print_serve_web_urls("code serve-web --host 0.0.0.0 --port 8123 --server-base-path dev", folder_path="/tmp/work tree")

    rendered = record_console.export_text()

    assert "http://localhost:8123/dev/?folder=/tmp/work%20tree" in rendered
    assert "http://hostbox:8123/dev/?folder=/tmp/work%20tree" in rendered
    assert "http://192.168.1.5:8123/dev/?folder=/tmp/work%20tree" in rendered


def test_print_serve_web_urls_reports_random_port_mode(monkeypatch) -> None:
    record_console = Console(record=True, width=200)
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)
    _install_address_helper(monkeypatch, [])

    cli_nw_vscode_share.print_serve_web_urls("code serve-web --port 0", folder_path="/tmp/project")

    rendered = record_console.export_text()

    assert "random free port" in rendered
    assert "Folder: /tmp/project" in rendered
