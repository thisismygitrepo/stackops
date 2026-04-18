from __future__ import annotations

import getpass
import sys
from dataclasses import dataclass
from types import ModuleType

import pytest
import rich.console
import rich.prompt
from rich.console import Console

import stackops.scripts.python.helpers.helpers_devops.cli_device as cli_device
import stackops.utils.code as code_utils


@dataclass(slots=True)
class WifiState:
    display_count: int = 0
    manual_count: int = 0
    last_ssid: str | None = None


def _install_wifi_helper(
    monkeypatch: pytest.MonkeyPatch,
    *,
    try_result: bool,
    manual_result: bool,
    state: WifiState,
) -> None:
    package_module = ModuleType("stackops.scripts.python.helpers.helpers_network")
    helper_module = ModuleType("stackops.scripts.python.helpers.helpers_network.wifi_conn")

    def display_available_networks() -> None:
        state.display_count += 1

    def manual_network_selection() -> bool:
        state.manual_count += 1
        return manual_result

    def try_config_connection(ssid: str) -> bool:
        state.last_ssid = ssid
        return try_result

    setattr(helper_module, "display_available_networks", display_available_networks)
    setattr(helper_module, "manual_network_selection", manual_network_selection)
    setattr(helper_module, "try_config_connection", try_config_connection)
    setattr(package_module, "wifi_conn", helper_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_network", package_module)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_network.wifi_conn", helper_module)


def test_bind_wsl_port_builds_portproxy_script(monkeypatch: pytest.MonkeyPatch) -> None:
    scripts: list[str] = []
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", lambda script: scripts.append(script))

    cli_device.bind_wsl_port(8080)

    assert len(scripts) == 1
    assert "listenport=8080" in scripts[0]
    assert "connectport=8080" in scripts[0]


def test_wifi_select_list_mode_only_displays_networks(monkeypatch: pytest.MonkeyPatch) -> None:
    state = WifiState()
    record_console = Console(record=True, width=120)
    _install_wifi_helper(monkeypatch, try_result=False, manual_result=False, state=state)
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)

    cli_device.wifi_select(ssid="Cafe", manual=False, list_=True)

    assert state.display_count == 1
    assert state.manual_count == 0
    assert state.last_ssid is None


def test_wifi_select_falls_back_to_manual_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    state = WifiState()
    record_console = Console(record=True, width=120)
    _install_wifi_helper(monkeypatch, try_result=False, manual_result=True, state=state)
    monkeypatch.setattr(rich.console, "Console", lambda: record_console)
    monkeypatch.setattr(rich.prompt.Confirm, "ask", lambda *_args, **_kwargs: True)

    cli_device.wifi_select(ssid="Cafe", manual=False, list_=False)

    rendered = record_console.export_text()

    assert state.last_ssid == "Cafe"
    assert state.manual_count == 1
    assert "Attempting to connect to configured network: Cafe" in rendered
    assert "Successfully connected!" in rendered


def test_reset_cloudflare_tunnel_background_mode_runs_confirmed_script(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[str] = []
    executed: list[str] = []
    monkeypatch.setattr(getpass, "getuser", lambda: "alex")
    monkeypatch.setattr(code_utils, "print_code", lambda code, **_kwargs: printed.append(code))
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", lambda code: executed.append(code))
    monkeypatch.setattr(cli_device.typer, "confirm", lambda *_args, **_kwargs: True)

    cli_device.reset_cloudflare_tunnel(task="oneoff-background-process", tunnel_name="demo")

    assert len(printed) == 1
    assert len(executed) == 1
    assert printed[0] == executed[0]
    assert "systemd-run" in executed[0]
    assert "User=alex" in executed[0]
    assert "tunnel run demo" in executed[0]
