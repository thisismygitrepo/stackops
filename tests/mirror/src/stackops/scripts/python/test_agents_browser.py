from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents_browser
from stackops.scripts.python.helpers.helpers_agents import agents_browser_launch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import REMOTE_DEBUGGING_LAN, BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    BrowserLaunchResult,
    DetachedBrowserLaunchResult,
)
from stackops.utils.network.address import InterfaceIPv4Address


type LaunchCall = tuple[BrowserName, int, str | None, bool, bool]


def test_launch_browser_lan_selects_address_before_launch_and_renders_it(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_preferences: list[bool] = []
    launch_calls: list[LaunchCall] = []
    selected_address = InterfaceIPv4Address(
        interface="Ethernet",
        ipv4_address="10.0.26.200",
        mac_address="00:11:22:33:44:55",
    )

    def select_address(prefer_vpn: bool) -> InterfaceIPv4Address:
        selector_preferences.append(prefer_vpn)
        return selected_address

    def launch(
        *,
        browser: BrowserName,
        port: int,
        profile_name: str | None,
        lan: bool,
        detached: bool,
    ) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, lan, detached))
        return DetachedBrowserLaunchResult(
            browser=browser,
            browser_path=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            command=("chrome.exe",),
            endpoint_label="Chrome DevTools Protocol",
            endpoint_short_label="CDP",
            process_label="Chrome",
            host=REMOTE_DEBUGGING_LAN,
            port=port,
            browser_port=57632,
            profile_path=Path("C:/Users/eng_a/data/browsers-profiles/chrome/p1"),
            prompt_path=Path("C:/Users/eng_a/code/agents/browser/vercel/prompts/chrome-p1-p9000.md"),
            process_id=30852,
            relay_process_id=17176,
        )

    monkeypatch.setattr(agents_browser, "select_lan_interface_ipv4", select_address)
    monkeypatch.setattr(agents_browser_launch, "launch_browser", launch)

    result = CliRunner().invoke(
        agents_browser.get_app(),
        ["launch-browser", "--port", "9000", "--detached", "--lan", "--profile", "p1"],
        terminal_width=140,
    )

    assert result.exit_code == 0, result.output
    assert selector_preferences == [False]
    assert launch_calls == [("chrome", 9000, "p1", True, True)]
    assert "Chrome launched" in result.output
    assert "http://10.0.26.200:9000" in result.output
    assert "Ethernet" in result.output
    assert "LAN exposure" in result.output


def test_launch_browser_lan_exits_before_launch_when_address_selection_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_preferences: list[bool] = []
    launch_calls: list[LaunchCall] = []

    def select_address(prefer_vpn: bool) -> None:
        selector_preferences.append(prefer_vpn)

    def launch(
        *,
        browser: BrowserName,
        port: int,
        profile_name: str | None,
        lan: bool,
        detached: bool,
    ) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, lan, detached))
        raise AssertionError("Browser launch must not run without a selected LAN address")

    monkeypatch.setattr(agents_browser, "select_lan_interface_ipv4", select_address)
    monkeypatch.setattr(agents_browser_launch, "launch_browser", launch)

    result = CliRunner().invoke(agents_browser.get_app(), ["launch-browser", "--lan"])

    assert result.exit_code == 1, result.output
    assert selector_preferences == [False]
    assert launch_calls == []
    assert "Could not determine a local LAN IPv4 address" in result.output
