from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_impl
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import AGENT_BROWSER_SKILL_REPO, BrowserName


@dataclass(frozen=True)
class FakeProcess:
    pid: int


def test_install_agent_browser_skill_confirms_local_skill_install(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}
    install_root = tmp_path / "browser" / "vercel"

    def fake_main_installer_cli(*, which: str, group: bool, interactive: bool, update: bool, version: str | None) -> None:
        observed["installer"] = {
            "which": which,
            "group": group,
            "interactive": interactive,
            "update": update,
            "version": version,
        }

    def fake_run_required_command(*, command: tuple[str, ...], cwd: Path) -> None:
        observed["command"] = command
        observed["cwd"] = cwd

    monkeypatch.setattr(agents_browser_impl, "BROWSING_ROOT", install_root)
    monkeypatch.setattr(
        "stackops.utils.installer_utils.installer_cli.main_installer_cli",
        fake_main_installer_cli,
    )
    monkeypatch.setattr(agents_browser_impl, "_run_required_command", fake_run_required_command)

    result = agents_browser_impl.install_agent_browser_skill()

    assert result.install_root == install_root
    assert result.command == ("bunx", "skills@latest", "add", AGENT_BROWSER_SKILL_REPO, "--yes")
    assert observed["command"] == result.command
    assert observed["cwd"] == install_root
    assert observed["installer"] == {
        "which": "agent-browser",
        "group": False,
        "interactive": False,
        "update": True,
        "version": None,
    }


def test_launch_browser_uses_isolated_profile_and_localhost_cdp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}
    browser_path = tmp_path / "chrome"
    profile_path = tmp_path / "profile"
    browsing_root = tmp_path / "browser-root"

    def fake_start_browser_process(*, command: Sequence[str], system_name: str, process_label: str) -> FakeProcess:
        observed["browser_command"] = tuple(command)
        observed["browser_system_name"] = system_name
        observed["process_label"] = process_label
        return FakeProcess(pid=41)

    def fake_assert_tcp_port_available(*, host: str, port: int) -> None:
        observed["port_probe"] = (host, port)

    def fake_platform_system() -> str:
        return "TestOS"

    def fake_resolve_browser_executable(*, browser: BrowserName) -> Path:
        observed["browser"] = browser
        return browser_path

    def fake_resolve_profile_path(*, browser: BrowserName, profile_name: str | None, port: int) -> Path:
        observed["profile_args"] = (browser, profile_name, port)
        return profile_path

    monkeypatch.setattr(agents_browser_impl, "BROWSING_ROOT", browsing_root)
    monkeypatch.setattr(agents_browser_impl.platform, "system", fake_platform_system)
    monkeypatch.setattr(agents_browser_impl, "resolve_browser_executable", fake_resolve_browser_executable)
    monkeypatch.setattr(agents_browser_impl, "resolve_profile_path", fake_resolve_profile_path)
    monkeypatch.setattr(agents_browser_impl, "_start_browser_process", fake_start_browser_process)
    monkeypatch.setattr(agents_browser_impl, "_assert_tcp_port_available", fake_assert_tcp_port_available)

    result = agents_browser_impl.launch_browser(browser="chrome", port=9331, profile_name="agent-browser", lan=False)

    assert result.host == "127.0.0.1"
    assert result.port == 9331
    assert result.browser_port == 9331
    assert result.process_id == 41
    assert result.relay_process_id is None
    assert result.endpoint_short_label == "CDP"
    assert result.process_label == "Chrome"
    assert result.profile_path == profile_path
    assert result.prompt_path == browsing_root / "prompt.md"
    assert observed["process_label"] == "Chrome"
    assert observed["port_probe"] == ("127.0.0.1", 9331)
    assert observed["profile_args"] == ("chrome", "agent-browser", 9331)
    assert observed["browser_command"] == (
        str(browser_path),
        "--remote-debugging-port=9331",
        f"--user-data-dir={profile_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    )
    prompt_text = result.prompt_path.read_text(encoding="utf-8")
    assert "with `--cdp 9331`" in prompt_text


def test_launch_browser_lan_uses_localhost_browser_and_lan_relay(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}
    browser_path = tmp_path / "chrome"
    profile_path = tmp_path / "profile"
    browsing_root = tmp_path / "browser-root"

    def fake_start_browser_process(*, command: Sequence[str], system_name: str, process_label: str) -> FakeProcess:
        observed["browser_command"] = tuple(command)
        observed["browser_system_name"] = system_name
        observed["process_label"] = process_label
        return FakeProcess(pid=51)

    def fake_start_endpoint_relay(*, listen_port: int, target_port: int, system_name: str) -> FakeProcess:
        observed["relay"] = {
            "listen_port": listen_port,
            "target_port": target_port,
            "system_name": system_name,
        }
        return FakeProcess(pid=52)

    def fake_assert_tcp_port_available(*, host: str, port: int) -> None:
        observed["port_probe"] = (host, port)

    def fake_platform_system() -> str:
        return "TestOS"

    def fake_resolve_browser_executable(*, browser: BrowserName) -> Path:
        observed["browser"] = browser
        return browser_path

    def fake_resolve_profile_path(*, browser: BrowserName, profile_name: str | None, port: int) -> Path:
        observed["profile_args"] = (browser, profile_name, port)
        return profile_path

    def fake_find_available_localhost_port(*, excluded_port: int) -> int:
        observed["excluded_port"] = excluded_port
        return 41837

    monkeypatch.setattr(agents_browser_impl, "BROWSING_ROOT", browsing_root)
    monkeypatch.setattr(agents_browser_impl.platform, "system", fake_platform_system)
    monkeypatch.setattr(agents_browser_impl, "resolve_browser_executable", fake_resolve_browser_executable)
    monkeypatch.setattr(agents_browser_impl, "resolve_profile_path", fake_resolve_profile_path)
    monkeypatch.setattr(agents_browser_impl, "_start_browser_process", fake_start_browser_process)
    monkeypatch.setattr(agents_browser_impl, "_start_endpoint_relay", fake_start_endpoint_relay)
    monkeypatch.setattr(agents_browser_impl, "_assert_tcp_port_available", fake_assert_tcp_port_available)
    monkeypatch.setattr(agents_browser_impl, "_find_available_localhost_port", fake_find_available_localhost_port)

    result = agents_browser_impl.launch_browser(browser="chrome", port=9331, profile_name="agent-browser", lan=True)

    assert result.host == "0.0.0.0"
    assert result.port == 9331
    assert result.browser_port == 41837
    assert result.process_id == 51
    assert result.relay_process_id == 52
    assert observed["process_label"] == "Chrome"
    assert observed["port_probe"] == ("0.0.0.0", 9331)
    assert observed["excluded_port"] == 9331
    assert observed["profile_args"] == ("chrome", "agent-browser", 9331)
    assert observed["browser_command"] == (
        str(browser_path),
        "--remote-debugging-port=41837",
        f"--user-data-dir={profile_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    )
    assert observed["relay"] == {
        "listen_port": 9331,
        "target_port": 41837,
        "system_name": "TestOS",
    }
    prompt_text = result.prompt_path.read_text(encoding="utf-8")
    assert "connect from the agent machine to `http://<LAN-IP>:9331`" in prompt_text
    assert "0.0.0.0:9331 to Chrome's localhost-only Chrome DevTools Protocol endpoint at 127.0.0.1:41837" in prompt_text


def test_launch_firefox_uses_bidi_endpoint_and_firefox_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}
    browser_path = tmp_path / "firefox"
    profile_path = tmp_path / "profile"
    browsing_root = tmp_path / "browser-root"

    def fake_start_browser_process(*, command: Sequence[str], system_name: str, process_label: str) -> FakeProcess:
        observed["browser_command"] = tuple(command)
        observed["browser_system_name"] = system_name
        observed["process_label"] = process_label
        return FakeProcess(pid=61)

    def fake_assert_tcp_port_available(*, host: str, port: int) -> None:
        observed["port_probe"] = (host, port)

    def fake_platform_system() -> str:
        return "TestOS"

    def fake_resolve_browser_executable(*, browser: BrowserName) -> Path:
        observed["browser"] = browser
        return browser_path

    def fake_resolve_profile_path(*, browser: BrowserName, profile_name: str | None, port: int) -> Path:
        observed["profile_args"] = (browser, profile_name, port)
        return profile_path

    monkeypatch.setattr(agents_browser_impl, "BROWSING_ROOT", browsing_root)
    monkeypatch.setattr(agents_browser_impl.platform, "system", fake_platform_system)
    monkeypatch.setattr(agents_browser_impl, "resolve_browser_executable", fake_resolve_browser_executable)
    monkeypatch.setattr(agents_browser_impl, "resolve_profile_path", fake_resolve_profile_path)
    monkeypatch.setattr(agents_browser_impl, "_start_browser_process", fake_start_browser_process)
    monkeypatch.setattr(agents_browser_impl, "_assert_tcp_port_available", fake_assert_tcp_port_available)

    result = agents_browser_impl.launch_browser(browser="firefox", port=9331, profile_name="agent-browser", lan=False)

    assert result.endpoint_short_label == "WebDriver BiDi"
    assert result.process_label == "Firefox"
    assert result.profile_path == profile_path
    assert observed["process_label"] == "Firefox"
    assert observed["profile_args"] == ("firefox", "agent-browser", 9331)
    assert observed["browser_command"] == (
        str(browser_path),
        "--remote-debugging-port",
        "9331",
        "--profile",
        str(profile_path),
        "--no-remote",
        "about:blank",
    )
    prompt_text = result.prompt_path.read_text(encoding="utf-8")
    assert "I launched Firefox with WebDriver BiDi enabled on 127.0.0.1:9331" in prompt_text
    assert "Use a WebDriver BiDi client against `http://127.0.0.1:9331`" in prompt_text


def test_launch_safari_uses_safaridriver_without_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}
    browser_path = tmp_path / "safaridriver"
    browsing_root = tmp_path / "browser-root"

    def fake_start_browser_process(*, command: Sequence[str], system_name: str, process_label: str) -> FakeProcess:
        observed["browser_command"] = tuple(command)
        observed["browser_system_name"] = system_name
        observed["process_label"] = process_label
        return FakeProcess(pid=71)

    def fake_assert_tcp_port_available(*, host: str, port: int) -> None:
        observed["port_probe"] = (host, port)

    def fake_platform_system() -> str:
        return "TestOS"

    def fake_resolve_browser_executable(*, browser: BrowserName) -> Path:
        observed["browser"] = browser
        return browser_path

    def fake_resolve_profile_path(*, browser: BrowserName, profile_name: str | None, port: int) -> None:
        observed["profile_args"] = (browser, profile_name, port)
        return None

    monkeypatch.setattr(agents_browser_impl, "BROWSING_ROOT", browsing_root)
    monkeypatch.setattr(agents_browser_impl.platform, "system", fake_platform_system)
    monkeypatch.setattr(agents_browser_impl, "resolve_browser_executable", fake_resolve_browser_executable)
    monkeypatch.setattr(agents_browser_impl, "resolve_profile_path", fake_resolve_profile_path)
    monkeypatch.setattr(agents_browser_impl, "_start_browser_process", fake_start_browser_process)
    monkeypatch.setattr(agents_browser_impl, "_assert_tcp_port_available", fake_assert_tcp_port_available)

    result = agents_browser_impl.launch_browser(browser="safari", port=9331, profile_name=None, lan=False)

    assert result.endpoint_short_label == "WebDriver"
    assert result.process_label == "safaridriver"
    assert result.profile_path is None
    assert observed["process_label"] == "safaridriver"
    assert observed["profile_args"] == ("safari", None, 9331)
    assert observed["browser_command"] == (str(browser_path), "--port", "9331")
    prompt_text = result.prompt_path.read_text(encoding="utf-8")
    assert "I launched Safari with WebDriver enabled on 127.0.0.1:9331" in prompt_text
    assert "Run `safaridriver --enable` once before first Safari WebDriver use." in prompt_text
