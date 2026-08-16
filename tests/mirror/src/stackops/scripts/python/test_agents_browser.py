from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents_browser
from stackops.scripts.python.helpers.helpers_agents import agents_browser_batch, agents_browser_launch, agents_browser_profiles
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import REMOTE_DEBUGGING_LAN, BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchResult, DetachedBrowserLaunchResult
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import BrowserProfileDeclutterResult, BrowserProfileReplicationResult
from stackops.utils.network.address import InterfaceIPv4Address


type LaunchCall = tuple[BrowserName, int, str | None, bool, bool]


def test_launch_browser_lan_selects_address_before_launch_and_renders_it(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_preferences: list[bool] = []
    launch_calls: list[LaunchCall] = []
    selected_address = InterfaceIPv4Address(interface="Ethernet", ipv4_address="10.0.26.200", mac_address="00:11:22:33:44:55")

    def select_address(prefer_vpn: bool) -> InterfaceIPv4Address:
        selector_preferences.append(prefer_vpn)
        return selected_address

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, lan: bool, detached: bool) -> BrowserLaunchResult:
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
        agents_browser.get_app(), ["launch-browser", "--port", "9000", "--detached", "--lan", "--profile", "p1"], terminal_width=140
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

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, lan, detached))
        raise AssertionError("Browser launch must not run without a selected LAN address")

    monkeypatch.setattr(agents_browser, "select_lan_interface_ipv4", select_address)
    monkeypatch.setattr(agents_browser_launch, "launch_browser", launch)

    result = CliRunner().invoke(agents_browser.get_app(), ["launch-browser", "--lan"])

    assert result.exit_code == 1, result.output
    assert selector_preferences == [False]
    assert launch_calls == []
    assert "Could not determine a local LAN IPv4 address" in result.output


def test_launch_browsers_launches_every_saved_profile_on_assigned_ports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_root = profiles_root.joinpath("chrome")
    for profile_name in ("p2", "base", "p1"):
        chrome_root.joinpath(profile_name).mkdir(parents=True)
    chrome_root.joinpath("README.txt").write_text("not a profile", encoding="utf-8")
    launch_calls: list[LaunchCall] = []

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, lan, detached))
        assert profile_name is not None
        return DetachedBrowserLaunchResult(
            browser=browser,
            browser_path=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            command=("chrome.exe",),
            endpoint_label="Chrome DevTools Protocol",
            endpoint_short_label="CDP",
            process_label="Chrome",
            host="127.0.0.1",
            port=port,
            browser_port=port,
            profile_path=chrome_root.joinpath(profile_name),
            prompt_path=tmp_path.joinpath(f"{profile_name}.md"),
            process_id=1000 + port,
            relay_process_id=None,
        )

    monkeypatch.setattr(agents_browser_batch, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_launch, "launch_browser", launch)

    result = CliRunner().invoke(
        agents_browser.get_app(), ["launch-browsers", "--browser", "chrome", "--port-start", "61000", "--detached"], terminal_width=180
    )

    assert result.exit_code == 0, result.output
    assert launch_calls == [("chrome", 61001, "p1", False, True), ("chrome", 61002, "p2", False, True), ("chrome", 61003, "base", False, True)]
    assert "Chrome profiles ready · 3 endpoint(s)" in result.output
    assert "p1" in result.output
    assert "p2" in result.output
    assert "base" in result.output
    assert "127.0.0.1" in result.output
    assert "61001" in result.output
    assert "61003" in result.output


def test_launch_browsers_is_listed_with_uppercase_alias() -> None:
    runner = CliRunner()

    help_result = runner.invoke(agents_browser.get_app(), ["--help"], terminal_width=140)
    alias_help_result = runner.invoke(agents_browser.get_app(), ["L", "--help"], terminal_width=140)

    assert help_result.exit_code == 0, help_result.output
    assert "launch-browsers" in help_result.output
    assert "<L> Launch every saved profile for one browser" in help_result.output
    assert alias_help_result.exit_code == 0, alias_help_result.output
    assert "--port-start" in alias_help_result.output
    assert "60000" in alias_help_result.output
    assert "--max-profiles" in alias_help_result.output


def test_launch_browsers_caps_requested_count_to_available_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    firefox_root = profiles_root.joinpath("firefox")
    firefox_root.joinpath("p1").mkdir(parents=True)
    firefox_root.joinpath("p2").mkdir()
    launch_calls: list[LaunchCall] = []

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, lan, detached))
        assert profile_name is not None
        return DetachedBrowserLaunchResult(
            browser=browser,
            browser_path=Path("C:/Program Files/Mozilla Firefox/firefox.exe"),
            command=("firefox.exe",),
            endpoint_label="WebDriver BiDi",
            endpoint_short_label="BiDi",
            process_label="Firefox",
            host="127.0.0.1",
            port=port,
            browser_port=port,
            profile_path=firefox_root.joinpath(profile_name),
            prompt_path=tmp_path.joinpath(f"{profile_name}.md"),
            process_id=port,
            relay_process_id=None,
        )

    monkeypatch.setattr(agents_browser_batch, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_launch, "launch_browser", launch)

    limited_result = CliRunner().invoke(agents_browser.get_app(), ["L", "--browser", "firefox", "-n", "1", "--detached"])

    assert limited_result.exit_code == 0, limited_result.output
    assert launch_calls == [("firefox", 60001, "p1", False, True)]
    assert "Firefox profiles ready · 1 endpoint(s)" in limited_result.output

    launch_calls.clear()
    available_result = CliRunner().invoke(agents_browser.get_app(), ["L", "--browser", "firefox", "-n", "5", "--detached"])

    assert available_result.exit_code == 0, available_result.output
    assert launch_calls == [("firefox", 60001, "p1", False, True), ("firefox", 60002, "p2", False, True)]
    assert "Firefox profiles ready · 2 endpoint(s)" in available_result.output


def test_declutter_defaults_to_chrome_and_reports_recovered_size(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[BrowserName, str]] = []

    def declutter(*, browser: BrowserName, profile_name: str) -> BrowserProfileDeclutterResult:
        calls.append((browser, profile_name))
        return BrowserProfileDeclutterResult(
            browser=browser,
            profile_path=Path("C:/Users/eng_a/data/browsers-profiles/chrome/base"),
            removed_paths=(Path("OptGuideOnDeviceModel"), Path("Default/Cache")),
            size_before_bytes=5 * 1024 * 1024,
            size_after_bytes=1 * 1024 * 1024,
            recovered_bytes=4 * 1024 * 1024,
        )

    monkeypatch.setattr(agents_browser_profiles, "declutter_browser_profile", declutter)

    result = CliRunner().invoke(agents_browser.get_app(), ["declutter", "--profile", "base"])

    assert result.exit_code == 0, result.output
    assert calls == [("chrome", "base")]
    assert "Removed paths: 2" in result.output
    assert "Recovered: 4.0 MiB" in result.output
    assert "Profile size: 1.0 MiB" in result.output


def test_replicate_defaults_to_chrome_base_and_forwards_count(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[BrowserName, str, int]] = []

    def replicate(*, browser: BrowserName, profile_name: str, count: int) -> BrowserProfileReplicationResult:
        calls.append((browser, profile_name, count))
        return BrowserProfileReplicationResult(
            browser=browser,
            source_path=Path("C:/Users/eng_a/data/browsers-profiles/chrome/base"),
            destination_paths=(Path("p1"), Path("p2"), Path("p3")),
            source_size_bytes=2 * 1024 * 1024,
        )

    monkeypatch.setattr(agents_browser_profiles, "replicate_browser_profile", replicate)

    result = CliRunner().invoke(agents_browser.get_app(), ["replicate", "3"])

    assert result.exit_code == 0, result.output
    assert calls == [("chrome", "base", 3)]
    assert result.output.count("Created:") == 3
    assert "Source size: 2.0 MiB" in result.output
