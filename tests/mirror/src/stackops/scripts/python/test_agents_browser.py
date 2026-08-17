from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents_browser
from stackops.scripts.python.helpers.helpers_agents import agents_browser_batch, agents_browser_launch, agents_browser_profiles
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import REMOTE_DEBUGGING_LAN, BrowserName, ProfileBrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchResult, DetachedBrowserLaunchResult
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import BrowserProfileDeclutterResult, BrowserProfileReplicationResult
from stackops.utils.network.address import InterfaceIPv4Address


type LaunchCall = tuple[BrowserName, int, str | None, bool, bool, bool]


def test_launch_browser_lan_selects_address_before_launch_and_renders_it(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_preferences: list[bool] = []
    launch_calls: list[LaunchCall] = []
    selected_address = InterfaceIPv4Address(interface="Ethernet", ipv4_address="10.0.26.200", mac_address="00:11:22:33:44:55")

    def select_address(prefer_vpn: bool) -> InterfaceIPv4Address:
        selector_preferences.append(prefer_vpn)
        return selected_address

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, temporary: bool, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, temporary, lan, detached))
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
        agents_browser.get_app(), ["launch-browser", "--port", "9000", "--detached", "--lan", "--profile", "p1", "-t"], terminal_width=140
    )

    assert result.exit_code == 0, result.output
    assert selector_preferences == [False]
    assert launch_calls == [("chrome", 9000, "p1", True, True, True)]
    assert "Chrome launched" in result.output
    assert "http://10.0.26.200:9000" in result.output
    assert "Ethernet" in result.output
    assert "LAN exposure" in result.output


def test_launch_browser_lan_exits_before_launch_when_address_selection_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    selector_preferences: list[bool] = []
    launch_calls: list[LaunchCall] = []

    def select_address(prefer_vpn: bool) -> None:
        selector_preferences.append(prefer_vpn)

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, temporary: bool, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, temporary, lan, detached))
        raise AssertionError("Browser launch must not run without a selected LAN address")

    monkeypatch.setattr(agents_browser, "select_lan_interface_ipv4", select_address)
    monkeypatch.setattr(agents_browser_launch, "launch_browser", launch)

    result = CliRunner().invoke(agents_browser.get_app(), ["launch-browser", "--lan"])

    assert result.exit_code == 1, result.output
    assert selector_preferences == [False]
    assert launch_calls == []
    assert "Could not determine a local LAN IPv4 address" in result.output


def test_batch_launch_launches_every_saved_profile_on_assigned_ports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_root = profiles_root.joinpath("chrome")
    for profile_name in ("p2", "base", "p1"):
        chrome_root.joinpath(profile_name).mkdir(parents=True)
    chrome_root.joinpath("README.txt").write_text("not a profile", encoding="utf-8")
    launch_calls: list[LaunchCall] = []

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, temporary: bool, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, temporary, lan, detached))
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
        agents_browser.get_app(), ["batch-launch", "--browser", "chrome", "--port-start", "61000", "--detached"], terminal_width=180
    )

    assert result.exit_code == 0, result.output
    assert launch_calls == [
        ("chrome", 61001, "p1", False, False, True),
        ("chrome", 61002, "p2", False, False, True),
        ("chrome", 61003, "base", False, False, True),
    ]
    assert "Chrome profiles ready · 3 endpoint(s)" in result.output
    assert "p1" in result.output
    assert "p2" in result.output
    assert "base" in result.output
    assert "127.0.0.1" in result.output
    assert "61001" in result.output
    assert "61003" in result.output


def test_batch_commands_are_listed_with_uppercase_aliases() -> None:
    runner = CliRunner()

    help_result = runner.invoke(agents_browser.get_app(), ["--help"], terminal_width=140)
    launch_alias_help_result = runner.invoke(agents_browser.get_app(), ["L", "--help"], terminal_width=140)
    single_launch_help_result = runner.invoke(agents_browser.get_app(), ["l", "--help"], terminal_width=140)
    close_alias_help_result = runner.invoke(agents_browser.get_app(), ["C", "--help"], terminal_width=140)
    old_command_result = runner.invoke(agents_browser.get_app(), ["launch-browsers", "--help"], terminal_width=140)

    assert help_result.exit_code == 0, help_result.output
    assert "batch-launch" in help_result.output
    assert "launch-browsers" not in help_result.output
    assert "<L> Launch every saved profile for one browser" in help_result.output
    assert "batch-close" in help_result.output
    assert "<C> Close tracked saved-profile browser launches" in help_result.output
    assert launch_alias_help_result.exit_code == 0, launch_alias_help_result.output
    assert single_launch_help_result.exit_code == 0, single_launch_help_result.output
    assert "--tmp" in single_launch_help_result.output
    assert "-t" in single_launch_help_result.output
    assert "--port-start" in launch_alias_help_result.output
    assert "60000" in launch_alias_help_result.output
    assert "--max-profiles" in launch_alias_help_result.output
    assert close_alias_help_result.exit_code == 0, close_alias_help_result.output
    assert "--browser" in close_alias_help_result.output
    assert old_command_result.exit_code == 2, old_command_result.output


def test_batch_launch_caps_requested_count_to_available_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    firefox_root = profiles_root.joinpath("firefox")
    firefox_root.joinpath("p1").mkdir(parents=True)
    firefox_root.joinpath("p2").mkdir()
    launch_calls: list[LaunchCall] = []

    def launch(*, browser: BrowserName, port: int, profile_name: str | None, temporary: bool, lan: bool, detached: bool) -> BrowserLaunchResult:
        launch_calls.append((browser, port, profile_name, temporary, lan, detached))
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
    assert launch_calls == [("firefox", 60001, "p1", False, False, True)]
    assert "Firefox profiles ready · 1 endpoint(s)" in limited_result.output

    launch_calls.clear()
    available_result = CliRunner().invoke(agents_browser.get_app(), ["L", "--browser", "firefox", "-n", "5", "--detached"])

    assert available_result.exit_code == 0, available_result.output
    assert launch_calls == [("firefox", 60001, "p1", False, False, True), ("firefox", 60002, "p2", False, False, True)]
    assert "Firefox profiles ready · 2 endpoint(s)" in available_result.output


def test_launch_browser_tmp_requires_a_named_profile() -> None:
    result = CliRunner().invoke(agents_browser.get_app(), ["launch-browser", "--tmp"])

    assert result.exit_code == 2, result.output
    assert "--tmp requires --profile" in result.output


def test_batch_close_closes_selected_browser_launches_across_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    close_calls: list[ProfileBrowserName] = []

    def close(*, browser: ProfileBrowserName) -> agents_browser_batch.BrowserProfileCloseResult:
        close_calls.append(browser)
        return agents_browser_batch.BrowserProfileCloseResult(
            browser=browser, tmux_launch_ids=("brave-profile-p1", "brave-profile-p2"), detached_launch_ids=("brave-profile-p3",)
        )

    monkeypatch.setattr(agents_browser_batch, "close_browser_profile_launches", close)

    result = CliRunner().invoke(agents_browser.get_app(), ["batch-close", "--browser", "brave"])

    assert result.exit_code == 0, result.output
    assert close_calls == ["brave"]
    assert "Closed 3 Brave saved-profile launch(es) (2 tmux, 1 detached)." in result.output


def test_batch_close_is_idempotent_when_no_launches_are_active(monkeypatch: pytest.MonkeyPatch) -> None:
    def close(*, browser: ProfileBrowserName) -> agents_browser_batch.BrowserProfileCloseResult:
        return agents_browser_batch.BrowserProfileCloseResult(browser=browser, tmux_launch_ids=(), detached_launch_ids=())

    monkeypatch.setattr(agents_browser_batch, "close_browser_profile_launches", close)

    result = CliRunner().invoke(agents_browser.get_app(), ["batch-close"])

    assert result.exit_code == 0, result.output
    assert "No active Chrome saved-profile launches found." in result.output


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
