from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution import (
    build_browser_launch_command,
    resolve_profile_path,
)


def test_safari_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Safari does not support --profile"):
        resolve_profile_path(browser="safari", profile_name="agent-browser", port=9331)


def test_safari_without_profile_has_no_profile_path() -> None:
    assert resolve_profile_path(browser="safari", profile_name=None, port=9331) is None


def test_firefox_launch_command_uses_bidi_remote_agent_with_profile(tmp_path: Path) -> None:
    browser_path = tmp_path / "firefox"
    profile_path = tmp_path / "profile"

    command = build_browser_launch_command(browser="firefox", browser_path=browser_path, port=9331, profile_path=profile_path)

    assert command == (
        str(browser_path),
        "--remote-debugging-port",
        "9331",
        "--profile",
        str(profile_path),
        "--no-remote",
        "about:blank",
    )


def test_safari_launch_command_starts_safaridriver_endpoint(tmp_path: Path) -> None:
    browser_path = tmp_path / "safaridriver"

    command = build_browser_launch_command(browser="safari", browser_path=browser_path, port=9331, profile_path=None)

    assert command == (str(browser_path), "--port", "9331")
