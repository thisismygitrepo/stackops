from contextlib import nullcontext
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_close
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_status import DetachedBrowserLaunchRecord
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import BrowserTmuxMetadata, BrowserTmuxPaneStatus


def _tmux_row(*, launch_id: str, role: str, browser: str, profile_path: Path, port: int, window_id: str) -> BrowserTmuxPaneStatus:
    return BrowserTmuxPaneStatus(
        session_name="stackops-browser",
        window_index="1",
        window_id=window_id,
        window_name=f"window-{window_id}",
        pane_index="0",
        pane_id=f"pane-{window_id}",
        pane_pid="1234",
        pane_current_command="chrome",
        pane_dead=False,
        pane_current_path=str(profile_path),
        metadata=BrowserTmuxMetadata(
            launch_id=launch_id,
            role=role,
            browser=browser,
            profile=f"profile-{profile_path.name}",
            profile_path=str(profile_path),
            host="127.0.0.1",
            port=str(port),
            browser_port=str(port),
            lan="yes" if role == "relay" else "no",
            prompt_path="prompt.md",
        ),
    )


def test_close_named_browser_profile_launches_closes_exact_tmux_windows_for_requested_profiles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_p1 = profiles_root.joinpath("chrome", "p1")
    chrome_p1_copy = chrome_p1.joinpath(".tmp", "bright-broker")
    chrome_p2 = profiles_root.joinpath("chrome", "p2")
    firefox_p1 = profiles_root.joinpath("firefox", "p1")
    temp_profile = tmp_path.joinpath("temp-profiles", "chrome", "port-9331")
    rows = (
        _tmux_row(launch_id="chrome-p1", role="endpoint", browser="chrome", profile_path=chrome_p1, port=60001, window_id="%1"),
        _tmux_row(launch_id="chrome-p1", role="relay", browser="chrome", profile_path=chrome_p1, port=60001, window_id="%2"),
        _tmux_row(launch_id="chrome-p1-copy", role="endpoint", browser="chrome", profile_path=chrome_p1_copy, port=60002, window_id="%3"),
        _tmux_row(launch_id="chrome-p2", role="endpoint", browser="chrome", profile_path=chrome_p2, port=60003, window_id="%4"),
        _tmux_row(launch_id="chrome-temp", role="endpoint", browser="chrome", profile_path=temp_profile, port=9331, window_id="%5"),
        _tmux_row(launch_id="firefox-p1", role="endpoint", browser="firefox", profile_path=firefox_p1, port=60001, window_id="%6"),
    )
    close_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", tmp_path.joinpath("detached-launches"))
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: "tmux")
    monkeypatch.setattr(agents_browser_close, "collect_browser_tmux_status", lambda: rows)
    monkeypatch.setattr(agents_browser_close, "close_browser_tmux_windows", lambda *, window_ids: close_calls.append(window_ids))

    result = agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=("p2", "p1"))

    assert close_calls == [("%1", "%2", "%3", "%4")]
    assert result.tmux_launch_ids == ("chrome-p1", "chrome-p1-copy", "chrome-p2")
    assert result.closed_count == 3


def test_close_named_browser_profile_launches_terminates_matching_detached_records(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    detached_root = tmp_path.joinpath("detached-launches")
    detached_root.mkdir()
    p1_record_path = detached_root.joinpath("chrome-p1.json")
    p1_copy_record_path = detached_root.joinpath("chrome-p1-copy.json")
    p2_record_path = detached_root.joinpath("chrome-p2.json")
    firefox_record_path = detached_root.joinpath("firefox-p1.json")
    for record_path in (p1_record_path, p1_copy_record_path, p2_record_path, firefox_record_path):
        record_path.write_text("{}", encoding="utf-8")
    records = {
        p1_record_path: _detached_record(
            launch_id="chrome-p1",
            browser="chrome",
            port=60001,
            profile_path=profiles_root.joinpath("chrome", "p1"),
            process_id=101,
            process_created_at=1.01,
        ),
        p1_copy_record_path: _detached_record(
            launch_id="chrome-p1-copy",
            browser="chrome",
            port=60002,
            profile_path=profiles_root.joinpath("chrome", "p1", ".tmp", "bright-broker"),
            process_id=202,
            process_created_at=2.02,
        ),
        p2_record_path: _detached_record(
            launch_id="chrome-p2",
            browser="chrome",
            port=60003,
            profile_path=profiles_root.joinpath("chrome", "p2"),
            process_id=303,
            process_created_at=3.03,
        ),
        firefox_record_path: _detached_record(
            launch_id="firefox-p1",
            browser="firefox",
            port=60001,
            profile_path=profiles_root.joinpath("firefox", "p1"),
            process_id=404,
            process_created_at=4.04,
        ),
    }
    termination_calls: list[int] = []

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", detached_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: None)
    monkeypatch.setattr(agents_browser_close, "read_detached_browser_launch", lambda *, record_path: records[record_path])
    monkeypatch.setattr(
        agents_browser_close,
        "terminate_browser_launch_process",
        lambda *, browser, browser_port, profile_path, process_id, process_created_at, process_label: termination_calls.append(process_id),
    )

    result = agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=("p1",))

    assert termination_calls == [202, 101]
    assert not p1_record_path.exists()
    assert not p1_copy_record_path.exists()
    assert p2_record_path.exists()
    assert firefox_record_path.exists()
    assert result.detached_launch_ids == ("chrome-p1-copy", "chrome-p1")
    assert result.closed_count == 2


def test_close_named_browser_profile_launches_rejects_empty_profile_names() -> None:
    with pytest.raises(ValueError, match="profile_names must not be empty"):
        agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=())


def test_close_named_browser_profile_launches_reports_failure_with_requested_profiles_headline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    detached_root = tmp_path.joinpath("detached-launches")
    detached_root.mkdir()
    failed_record_path = detached_root.joinpath("chrome-p1.json")
    failed_record_path.write_text("{}", encoding="utf-8")
    records = {
        failed_record_path: _detached_record(
            launch_id="chrome-p1",
            browser="chrome",
            port=60001,
            profile_path=tmp_path.joinpath("browsers-profiles", "chrome", "p1"),
            process_id=101,
            process_created_at=1.01,
        )
    }

    def fail_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        raise RuntimeError(f"Could not terminate {process_label} process {process_id}")

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", tmp_path.joinpath("browsers-profiles"))
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", detached_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: None)
    monkeypatch.setattr(agents_browser_close, "read_detached_browser_launch", lambda *, record_path: records[record_path])
    monkeypatch.setattr(agents_browser_close, "terminate_browser_launch_process", fail_termination)

    with pytest.raises(RuntimeError, match="Could not close every requested chrome profile launch \\(p1, p2\\)"):
        agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=("p1", "p2"))

    assert failed_record_path.exists()


def _detached_record(
    *,
    launch_id: str,
    browser: BrowserName,
    port: int,
    profile_path: Path,
    process_id: int,
    process_created_at: float,
    relay_process_id: int | None = None,
    relay_process_created_at: float | None = None,
) -> DetachedBrowserLaunchRecord:
    return DetachedBrowserLaunchRecord(
        launch_id=launch_id,
        browser=browser,
        profile=f"profile-{profile_path.name}",
        host="127.0.0.1",
        port=port,
        browser_port=port,
        profile_path=profile_path,
        process_id=process_id,
        process_created_at=process_created_at,
        relay_expected=relay_process_id is not None,
        relay_process_id=relay_process_id,
        relay_process_created_at=relay_process_created_at,
    )


def test_close_all_browser_profile_launches_closes_exact_tmux_windows_for_matching_browser(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_profile = profiles_root.joinpath("chrome", "p1")
    copied_chrome_profile = chrome_profile.joinpath(".tmp", "bright-broker")
    firefox_profile = profiles_root.joinpath("firefox", "p1")
    temp_profile = tmp_path.joinpath("temp-profiles", "chrome", "port-9331")
    rows = (
        _tmux_row(launch_id="chrome-p1", role="endpoint", browser="chrome", profile_path=chrome_profile, port=60001, window_id="%1"),
        _tmux_row(launch_id="chrome-p1", role="relay", browser="chrome", profile_path=chrome_profile, port=60001, window_id="%2"),
        _tmux_row(launch_id="chrome-temp", role="endpoint", browser="chrome", profile_path=temp_profile, port=9331, window_id="%3"),
        _tmux_row(launch_id="firefox-p1", role="endpoint", browser="firefox", profile_path=firefox_profile, port=60001, window_id="%4"),
        _tmux_row(launch_id="chrome-copied", role="endpoint", browser="chrome", profile_path=copied_chrome_profile, port=60002, window_id="%5"),
    )
    close_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", tmp_path.joinpath("detached-launches"))
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: "tmux")
    monkeypatch.setattr(agents_browser_close, "collect_browser_tmux_status", lambda: rows)
    monkeypatch.setattr(agents_browser_close, "close_browser_tmux_windows", lambda *, window_ids: close_calls.append(window_ids))

    result = agents_browser_close.close_all_browser_profile_launches(browser="chrome")

    assert close_calls == [("%1", "%2", "%5")]
    assert result.tmux_launch_ids == ("chrome-copied", "chrome-p1")
    assert result.detached_launch_ids == ()
    assert result.closed_count == 2


def test_close_browser_launch_closes_exact_tmux_windows_for_browser_and_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_profile = profiles_root.joinpath("chrome", "p1")
    temp_profile = tmp_path.joinpath("temp-profiles", "chrome", "port-9331")
    firefox_profile = profiles_root.joinpath("firefox", "p1")
    rows = (
        _tmux_row(launch_id="chrome-p1", role="endpoint", browser="chrome", profile_path=chrome_profile, port=9331, window_id="%1"),
        _tmux_row(launch_id="chrome-p1", role="relay", browser="chrome", profile_path=chrome_profile, port=9331, window_id="%2"),
        _tmux_row(launch_id="chrome-temp", role="endpoint", browser="chrome", profile_path=temp_profile, port=9332, window_id="%3"),
        _tmux_row(launch_id="firefox-p1", role="endpoint", browser="firefox", profile_path=firefox_profile, port=9331, window_id="%4"),
        _tmux_row(
            launch_id="chrome-other",
            role="endpoint",
            browser="chrome",
            profile_path=profiles_root.joinpath("chrome", "p2"),
            port=9333,
            window_id="%5",
        ),
    )
    close_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", tmp_path.joinpath("detached-launches"))
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: "tmux")
    monkeypatch.setattr(agents_browser_close, "collect_browser_tmux_status", lambda: rows)
    monkeypatch.setattr(agents_browser_close, "close_browser_tmux_windows", lambda *, window_ids: close_calls.append(window_ids))

    result = agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert close_calls == [("%1", "%2")]
    assert result.tmux_launch_ids == ("chrome-p1",)
    assert result.detached_launch_ids == ()
    assert result.closed_count == 1


def test_close_browser_launch_closes_port_scoped_tmux_launch_without_a_saved_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    temp_profile = tmp_path.joinpath("temp-profiles", "chrome", "port-9331")
    rows = (_tmux_row(launch_id="chrome-temp", role="endpoint", browser="chrome", profile_path=temp_profile, port=9331, window_id="%1"),)
    close_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", tmp_path.joinpath("browsers-profiles"))
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", tmp_path.joinpath("detached-launches"))
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: "tmux")
    monkeypatch.setattr(agents_browser_close, "collect_browser_tmux_status", lambda: rows)
    monkeypatch.setattr(agents_browser_close, "close_browser_tmux_windows", lambda *, window_ids: close_calls.append(window_ids))

    result = agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert close_calls == [("%1",)]
    assert result.tmux_launch_ids == ("chrome-temp",)
    assert result.closed_count == 1


def test_close_all_browser_profile_launches_terminates_registered_detached_processes_and_removes_matching_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    detached_root = tmp_path.joinpath("detached-launches")
    detached_root.mkdir()
    matching_record_path = detached_root.joinpath("chrome-p1.json")
    copied_record_path = detached_root.joinpath("chrome-z-copied.json")
    temp_record_path = detached_root.joinpath("chrome-temp.json")
    other_browser_record_path = detached_root.joinpath("firefox-p1.json")
    for record_path in (matching_record_path, copied_record_path, temp_record_path, other_browser_record_path):
        record_path.write_text("{}", encoding="utf-8")
    records = {
        matching_record_path: _detached_record(
            launch_id="chrome-p1",
            browser="chrome",
            port=60001,
            profile_path=profiles_root.joinpath("chrome", "p1"),
            process_id=101,
            process_created_at=1.01,
            relay_process_id=202,
            relay_process_created_at=2.02,
        ),
        copied_record_path: _detached_record(
            launch_id="chrome-z-copied",
            browser="chrome",
            port=60002,
            profile_path=profiles_root.joinpath("chrome", "base", ".tmp", "bright-broker"),
            process_id=505,
            process_created_at=5.05,
        ),
        temp_record_path: _detached_record(
            launch_id="chrome-temp",
            browser="chrome",
            port=9331,
            profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
            process_id=303,
            process_created_at=3.03,
        ),
        other_browser_record_path: _detached_record(
            launch_id="firefox-p1",
            browser="firefox",
            port=60001,
            profile_path=profiles_root.joinpath("firefox", "p1"),
            process_id=404,
            process_created_at=4.04,
        ),
    }
    relay_termination_calls: list[tuple[int, float, str]] = []
    browser_termination_calls: list[tuple[BrowserName, int, Path, int, float, str]] = []

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", detached_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: None)
    monkeypatch.setattr(agents_browser_close, "read_detached_browser_launch", lambda *, record_path: records[record_path])
    monkeypatch.setattr(
        agents_browser_close,
        "terminate_registered_process",
        lambda *, process_id, process_created_at, process_label: relay_termination_calls.append((process_id, process_created_at, process_label)),
    )
    monkeypatch.setattr(
        agents_browser_close,
        "terminate_browser_launch_process",
        lambda *, browser, browser_port, profile_path, process_id, process_created_at, process_label: browser_termination_calls.append(
            (browser, browser_port, profile_path, process_id, process_created_at, process_label)
        ),
    )

    result = agents_browser_close.close_all_browser_profile_launches(browser="chrome")

    assert relay_termination_calls == [(202, 2.02, "browser endpoint LAN relay")]
    assert browser_termination_calls == [
        ("chrome", 60001, profiles_root.joinpath("chrome", "p1"), 101, 1.01, "chrome browser"),
        ("chrome", 60002, profiles_root.joinpath("chrome", "base", ".tmp", "bright-broker"), 505, 5.05, "chrome browser"),
    ]
    assert not matching_record_path.exists()
    assert not copied_record_path.exists()
    assert temp_record_path.exists()
    assert other_browser_record_path.exists()
    assert result.tmux_launch_ids == ()
    assert result.detached_launch_ids == ("chrome-p1", "chrome-z-copied")
    assert result.closed_count == 2


def test_close_browser_launch_terminates_matching_detached_record_by_browser_and_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    detached_root = tmp_path.joinpath("detached-launches")
    detached_root.mkdir()
    matching_record_path = detached_root.joinpath("chrome-p1.json")
    other_port_record_path = detached_root.joinpath("chrome-p2.json")
    other_browser_record_path = detached_root.joinpath("firefox-p1.json")
    temp_record_path = detached_root.joinpath("chrome-temp.json")
    for record_path in (matching_record_path, other_port_record_path, other_browser_record_path, temp_record_path):
        record_path.write_text("{}", encoding="utf-8")
    records = {
        matching_record_path: _detached_record(
            launch_id="chrome-p1",
            browser="chrome",
            port=9331,
            profile_path=profiles_root.joinpath("chrome", "p1"),
            process_id=101,
            process_created_at=1.01,
        ),
        other_port_record_path: _detached_record(
            launch_id="chrome-p2",
            browser="chrome",
            port=9332,
            profile_path=profiles_root.joinpath("chrome", "p2"),
            process_id=202,
            process_created_at=2.02,
        ),
        other_browser_record_path: _detached_record(
            launch_id="firefox-p1",
            browser="firefox",
            port=9331,
            profile_path=profiles_root.joinpath("firefox", "p1"),
            process_id=303,
            process_created_at=3.03,
        ),
        temp_record_path: _detached_record(
            launch_id="chrome-temp",
            browser="chrome",
            port=9331,
            profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
            process_id=404,
            process_created_at=4.04,
        ),
    }
    termination_calls: list[int] = []

    def record_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        termination_calls.append(process_id)

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", detached_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: None)
    monkeypatch.setattr(agents_browser_close, "read_detached_browser_launch", lambda *, record_path: records[record_path])
    monkeypatch.setattr(agents_browser_close, "terminate_browser_launch_process", record_termination)

    result = agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert termination_calls == [101, 404]
    assert not matching_record_path.exists()
    assert not temp_record_path.exists()
    assert other_port_record_path.exists()
    assert other_browser_record_path.exists()
    assert result.tmux_launch_ids == ()
    assert result.detached_launch_ids == ("chrome-p1", "chrome-temp")
    assert result.closed_count == 2


def test_close_all_browser_profile_launches_keeps_failed_record_and_continues_with_later_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    detached_root = tmp_path.joinpath("detached-launches")
    detached_root.mkdir()
    failed_record_path = detached_root.joinpath("chrome-p1.json")
    successful_record_path = detached_root.joinpath("chrome-p2.json")
    failed_record_path.write_text("{}", encoding="utf-8")
    successful_record_path.write_text("{}", encoding="utf-8")
    records = {
        failed_record_path: _detached_record(
            launch_id="chrome-p1",
            browser="chrome",
            port=60001,
            profile_path=profiles_root.joinpath("chrome", "p1"),
            process_id=101,
            process_created_at=1.01,
        ),
        successful_record_path: _detached_record(
            launch_id="chrome-p2",
            browser="chrome",
            port=60002,
            profile_path=profiles_root.joinpath("chrome", "p2"),
            process_id=202,
            process_created_at=2.02,
        ),
    }
    termination_calls: list[int] = []

    def fail_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        termination_calls.append(process_id)
        if process_id == 101:
            raise RuntimeError(f"Could not terminate {process_label} process {process_id}")

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", detached_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: None)
    monkeypatch.setattr(agents_browser_close, "read_detached_browser_launch", lambda *, record_path: records[record_path])
    monkeypatch.setattr(agents_browser_close, "terminate_browser_launch_process", fail_termination)

    with pytest.raises(RuntimeError, match="Could not terminate chrome browser process 101"):
        agents_browser_close.close_all_browser_profile_launches(browser="chrome")

    assert termination_calls == [101, 202]
    assert failed_record_path.exists()
    assert not successful_record_path.exists()


def test_close_browser_launch_reports_failure_with_browser_and_port_headline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    detached_root = tmp_path.joinpath("detached-launches")
    detached_root.mkdir()
    failed_record_path = detached_root.joinpath("chrome-p1.json")
    failed_record_path.write_text("{}", encoding="utf-8")
    records = {
        failed_record_path: _detached_record(
            launch_id="chrome-p1",
            browser="chrome",
            port=9331,
            profile_path=tmp_path.joinpath("browsers-profiles", "chrome", "p1"),
            process_id=101,
            process_created_at=1.01,
        )
    }

    def fail_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        raise RuntimeError(f"Could not terminate {process_label} process {process_id}")

    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", tmp_path.joinpath("browsers-profiles"))
    monkeypatch.setattr(agents_browser_close, "BROWSER_DETACHED_LAUNCHES_ROOT", detached_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close.shutil, "which", lambda _name: None)
    monkeypatch.setattr(agents_browser_close, "read_detached_browser_launch", lambda *, record_path: records[record_path])
    monkeypatch.setattr(agents_browser_close, "terminate_browser_launch_process", fail_termination)

    with pytest.raises(RuntimeError, match="Could not close the chrome launch on port 9331"):
        agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert failed_record_path.exists()
