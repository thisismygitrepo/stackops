from contextlib import nullcontext
from pathlib import Path
from typing import Never

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_launch as browser_launch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchDetails


def test_temporary_launch_uses_copy_and_removes_it_when_launch_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_profile_path = tmp_path.joinpath("browsers-profiles", "chrome", "base")
    original_profile_path.mkdir(parents=True)
    copied_path = original_profile_path.joinpath(".tmp", "bright-broker")

    def resolve_profile(*, browser: BrowserName, profile_name: str | None, port: int) -> Path:
        assert (browser, profile_name, port) == ("chrome", "base", 9331)
        return original_profile_path

    def resolve_executable(*, browser: BrowserName) -> Path:
        assert browser == "chrome"
        return Path("/usr/bin/google-chrome")

    def prepare_state() -> None:
        return

    def copy_profile(*, browser: BrowserName, source_path: Path) -> Path:
        assert browser == "chrome"
        assert source_path == original_profile_path
        copied_path.mkdir(parents=True)
        copied_path.joinpath("partial-state.bin").write_bytes(b"state")
        return copied_path

    def fail_after_copy(*, browser: BrowserName, browser_path: Path, profile_path: Path | None, port: int, lan: bool) -> Never:
        assert browser == "chrome"
        assert browser_path == Path("/usr/bin/google-chrome")
        assert profile_path == copied_path
        assert (port, lan) == (9331, False)
        raise RuntimeError("port unavailable")

    monkeypatch.setattr(browser_launch, "browser_launch_lock", nullcontext)
    monkeypatch.setattr(browser_launch, "resolve_profile_path", resolve_profile)
    monkeypatch.setattr(browser_launch, "resolve_browser_executable", resolve_executable)
    monkeypatch.setattr(browser_launch, "prepare_browser_launch_state", prepare_state)
    monkeypatch.setattr(browser_launch, "copy_browser_profile_to_temporary", copy_profile)
    monkeypatch.setattr(browser_launch, "reuse_browser_launch_if_active", fail_after_copy)

    with pytest.raises(RuntimeError, match="port unavailable"):
        browser_launch.launch_browser(browser="chrome", port=9331, profile_name="base", temporary=True, lan=False, detached=True)

    assert original_profile_path.is_dir()
    assert not copied_path.exists()


def test_temporary_launch_preserves_copy_when_runtime_start_is_interrupted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_profile_path = tmp_path.joinpath("browsers-profiles", "chrome", "base")
    original_profile_path.mkdir(parents=True)
    copied_path = original_profile_path.joinpath(".tmp", "bright-broker")

    def resolve_profile(*, browser: BrowserName, profile_name: str | None, port: int) -> Path:
        assert (browser, profile_name, port) == ("chrome", "base", 9331)
        return original_profile_path

    def resolve_executable(*, browser: BrowserName) -> Path:
        assert browser == "chrome"
        return Path("/usr/bin/google-chrome")

    def prepare_state() -> None:
        return

    def copy_profile(*, browser: BrowserName, source_path: Path) -> Path:
        assert browser == "chrome"
        assert source_path == original_profile_path
        copied_path.mkdir(parents=True)
        return copied_path

    def no_existing_launch(*, browser: BrowserName, browser_path: Path, profile_path: Path | None, port: int, lan: bool) -> None:
        assert (browser, browser_path, profile_path, port, lan) == ("chrome", Path("/usr/bin/google-chrome"), copied_path, 9331, False)

    def resolve_endpoint_port(*, exposed_port: int, lan: bool) -> int:
        assert (exposed_port, lan) == (9331, False)
        return exposed_port

    def build_details(
        *, browser: BrowserName, browser_path: Path, profile_path: Path | None, port: int, browser_port: int, lan: bool
    ) -> BrowserLaunchDetails:
        assert (browser, browser_path, profile_path, port, browser_port, lan) == (
            "chrome",
            Path("/usr/bin/google-chrome"),
            copied_path,
            9331,
            9331,
            False,
        )
        return BrowserLaunchDetails(
            browser=browser,
            browser_path=browser_path,
            command=(str(browser_path),),
            endpoint_label="Chrome DevTools Protocol",
            endpoint_short_label="CDP",
            process_label="Chrome",
            host="127.0.0.1",
            port=port,
            browser_port=browser_port,
            profile_path=profile_path,
            prompt_path=tmp_path.joinpath("prompt.md"),
        )

    def interrupt_runtime(*, details: BrowserLaunchDetails, lan: bool) -> Never:
        assert details.profile_path == copied_path
        assert lan is False
        raise KeyboardInterrupt

    monkeypatch.setattr(browser_launch, "browser_launch_lock", nullcontext)
    monkeypatch.setattr(browser_launch, "resolve_profile_path", resolve_profile)
    monkeypatch.setattr(browser_launch, "resolve_browser_executable", resolve_executable)
    monkeypatch.setattr(browser_launch, "prepare_browser_launch_state", prepare_state)
    monkeypatch.setattr(browser_launch, "copy_browser_profile_to_temporary", copy_profile)
    monkeypatch.setattr(browser_launch, "reuse_browser_launch_if_active", no_existing_launch)
    monkeypatch.setattr(browser_launch, "resolve_browser_endpoint_port", resolve_endpoint_port)
    monkeypatch.setattr(browser_launch, "build_browser_launch_details", build_details)
    monkeypatch.setattr(browser_launch, "launch_detached_browser", interrupt_runtime)

    with pytest.raises(KeyboardInterrupt):
        browser_launch.launch_browser(browser="chrome", port=9331, profile_name="base", temporary=True, lan=False, detached=True)

    assert copied_path.is_dir()
