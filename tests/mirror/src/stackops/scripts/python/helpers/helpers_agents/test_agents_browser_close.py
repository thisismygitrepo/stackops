from contextlib import nullcontext
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_close, agents_browser_lifecycle
from stackops.scripts.python.helpers.helpers_agents.agents_browser_close import ClosedBrowserLaunch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserWindowHandle
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import BrowserLaunchRecord


def _record(
    *,
    launch_id: str,
    browser: BrowserName,
    port: int,
    profile_path: Path,
    process_id: int,
    process_created_at: float,
    relay_process_id: int | None = None,
    relay_process_created_at: float | None = None,
    windows: BrowserWindowHandle | None = None,
) -> BrowserLaunchRecord:
    return BrowserLaunchRecord(
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
        windows=windows,
    )


def _tmux_windows(*targets: str) -> BrowserWindowHandle:
    return BrowserWindowHandle(multiplexer="tmux", session_name="stackops-browser", targets=targets, attach_script="tmux attach")


def _install_records(
    *, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, profiles_root: Path, records: tuple[BrowserLaunchRecord, ...]
) -> dict[str, Path]:
    records_root = tmp_path.joinpath("launches")
    records_root.mkdir()
    record_paths = {record.launch_id: records_root.joinpath(f"{record.launch_id}.json") for record in records}
    for record_path in record_paths.values():
        record_path.write_text("{}", encoding="utf-8")
    records_by_path = {record_paths[record.launch_id]: record for record in records}
    monkeypatch.setattr(agents_browser_close, "BROWSER_PROFILES_ROOT", profiles_root)
    monkeypatch.setattr(agents_browser_close, "browser_launch_lock", lambda: nullcontext())
    monkeypatch.setattr(agents_browser_close, "list_browser_launch_record_paths", lambda: tuple(sorted(records_by_path)))
    monkeypatch.setattr(agents_browser_close, "read_browser_launch_record", lambda *, record_path: records_by_path[record_path])
    return record_paths


def _record_window_closes(*, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    close_calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(agents_browser_lifecycle, "terminate_registered_process", lambda *, process_id, process_created_at, process_label: None)
    monkeypatch.setattr(
        agents_browser_lifecycle,
        "terminate_browser_launch_process",
        lambda *, browser, browser_port, profile_path, process_id, process_created_at, process_label: None,
    )
    monkeypatch.setattr(agents_browser_lifecycle, "close_browser_windows", lambda *, handle: close_calls.append(handle.targets))
    return close_calls


def test_close_named_browser_profile_launches_closes_exact_tmux_windows_for_requested_profiles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_p1 = profiles_root.joinpath("chrome", "p1")
    temp_profile = tmp_path.joinpath("temp-profiles", "chrome", "port-9331")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=60001, profile_path=chrome_p1, process_id=1, process_created_at=1.0,
                relay_process_id=2, relay_process_created_at=2.0, windows=_tmux_windows("%1", "%2")),
        _record(launch_id="chrome-p1-copy", browser="chrome", port=60002, profile_path=chrome_p1.joinpath(".tmp", "bright-broker"), process_id=3,
                process_created_at=3.0, windows=_tmux_windows("%3")),
        _record(launch_id="chrome-p2", browser="chrome", port=60003, profile_path=profiles_root.joinpath("chrome", "p2"), process_id=4,
                process_created_at=4.0, windows=_tmux_windows("%4")),
        _record(launch_id="chrome-temp", browser="chrome", port=9331, profile_path=temp_profile, process_id=5, process_created_at=5.0,
                windows=_tmux_windows("%5")),
        _record(launch_id="firefox-p1", browser="firefox", port=60001, profile_path=profiles_root.joinpath("firefox", "p1"), process_id=6,
                process_created_at=6.0, windows=_tmux_windows("%6")),
    )
    _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    close_calls = _record_window_closes(monkeypatch=monkeypatch)

    result = agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=("p2", "p1"))

    assert close_calls == [("%3",), ("%1", "%2"), ("%4",)]
    assert result.closed == (
        ClosedBrowserLaunch(launch_id="chrome-p1-copy", runtime="tmux"),
        ClosedBrowserLaunch(launch_id="chrome-p1", runtime="tmux"),
        ClosedBrowserLaunch(launch_id="chrome-p2", runtime="tmux"),
    )


def test_close_named_browser_profile_launches_terminates_matching_detached_records(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=60001, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=101,
                process_created_at=1.01),
        _record(launch_id="chrome-p1-copy", browser="chrome", port=60002, profile_path=profiles_root.joinpath("chrome", "p1", ".tmp", "bright-broker"),
                process_id=202, process_created_at=2.02),
        _record(launch_id="chrome-p2", browser="chrome", port=60003, profile_path=profiles_root.joinpath("chrome", "p2"), process_id=303,
                process_created_at=3.03),
        _record(launch_id="firefox-p1", browser="firefox", port=60001, profile_path=profiles_root.joinpath("firefox", "p1"), process_id=404,
                process_created_at=4.04),
    )
    record_paths = _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    termination_calls: list[int] = []
    monkeypatch.setattr(
        agents_browser_lifecycle,
        "terminate_browser_launch_process",
        lambda *, browser, browser_port, profile_path, process_id, process_created_at, process_label: termination_calls.append(process_id),
    )

    result = agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=("p1",))

    assert termination_calls == [202, 101]
    assert not record_paths["chrome-p1"].exists()
    assert not record_paths["chrome-p1-copy"].exists()
    assert record_paths["chrome-p2"].exists()
    assert record_paths["firefox-p1"].exists()
    assert result.closed == (
        ClosedBrowserLaunch(launch_id="chrome-p1-copy", runtime="detached"),
        ClosedBrowserLaunch(launch_id="chrome-p1", runtime="detached"),
    )


def test_close_named_browser_profile_launches_rejects_empty_profile_names() -> None:
    with pytest.raises(ValueError, match="profile_names must not be empty"):
        agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=())


def test_close_named_browser_profile_launches_reports_failure_with_requested_profiles_headline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=60001, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=101,
                process_created_at=1.01),
    )
    record_paths = _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)

    def fail_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        raise RuntimeError(f"Could not terminate {process_label} process {process_id}")

    monkeypatch.setattr(agents_browser_lifecycle, "terminate_browser_launch_process", fail_termination)

    with pytest.raises(RuntimeError, match="Could not close every requested chrome profile launch \\(p1, p2\\)"):
        agents_browser_close.close_named_browser_profile_launches(browser="chrome", profile_names=("p1", "p2"))

    assert record_paths["chrome-p1"].exists()


def test_close_all_browser_profile_launches_closes_exact_tmux_windows_for_matching_browser(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    chrome_profile = profiles_root.joinpath("chrome", "p1")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=60001, profile_path=chrome_profile, process_id=1, process_created_at=1.0,
                relay_process_id=2, relay_process_created_at=2.0, windows=_tmux_windows("%1", "%2")),
        _record(launch_id="chrome-temp", browser="chrome", port=9331, profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
                process_id=3, process_created_at=3.0, windows=_tmux_windows("%3")),
        _record(launch_id="firefox-p1", browser="firefox", port=60001, profile_path=profiles_root.joinpath("firefox", "p1"), process_id=4,
                process_created_at=4.0, windows=_tmux_windows("%4")),
        _record(launch_id="chrome-copied", browser="chrome", port=60002, profile_path=chrome_profile.joinpath(".tmp", "bright-broker"), process_id=5,
                process_created_at=5.0, windows=_tmux_windows("%5")),
    )
    _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    close_calls = _record_window_closes(monkeypatch=monkeypatch)

    result = agents_browser_close.close_all_browser_profile_launches(browser="chrome")

    assert close_calls == [("%5",), ("%1", "%2")]
    assert result.closed == (
        ClosedBrowserLaunch(launch_id="chrome-copied", runtime="tmux"),
        ClosedBrowserLaunch(launch_id="chrome-p1", runtime="tmux"),
    )


def test_close_browser_launch_closes_exact_tmux_windows_for_browser_and_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=9331, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=1,
                process_created_at=1.0, relay_process_id=2, relay_process_created_at=2.0, windows=_tmux_windows("%1", "%2")),
        _record(launch_id="chrome-temp", browser="chrome", port=9332, profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
                process_id=3, process_created_at=3.0, windows=_tmux_windows("%3")),
        _record(launch_id="firefox-p1", browser="firefox", port=9331, profile_path=profiles_root.joinpath("firefox", "p1"), process_id=4,
                process_created_at=4.0, windows=_tmux_windows("%4")),
        _record(launch_id="chrome-other", browser="chrome", port=9333, profile_path=profiles_root.joinpath("chrome", "p2"), process_id=5,
                process_created_at=5.0, windows=_tmux_windows("%5")),
    )
    _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    close_calls = _record_window_closes(monkeypatch=monkeypatch)

    result = agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert close_calls == [("%1", "%2")]
    assert result.closed == (ClosedBrowserLaunch(launch_id="chrome-p1", runtime="tmux"),)


def test_close_browser_launch_closes_port_scoped_tmux_launch_without_a_saved_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    records = (
        _record(launch_id="chrome-temp", browser="chrome", port=9331, profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
                process_id=1, process_created_at=1.0, windows=_tmux_windows("%1")),
    )
    _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=tmp_path.joinpath("browsers-profiles"), records=records)
    close_calls = _record_window_closes(monkeypatch=monkeypatch)

    result = agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert close_calls == [("%1",)]
    assert result.closed == (ClosedBrowserLaunch(launch_id="chrome-temp", runtime="tmux"),)


def test_close_all_browser_profile_launches_terminates_registered_detached_processes_and_removes_matching_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=60001, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=101,
                process_created_at=1.01, relay_process_id=202, relay_process_created_at=2.02),
        _record(launch_id="chrome-z-copied", browser="chrome", port=60002,
                profile_path=profiles_root.joinpath("chrome", "base", ".tmp", "bright-broker"), process_id=505, process_created_at=5.05),
        _record(launch_id="chrome-temp", browser="chrome", port=9331, profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
                process_id=303, process_created_at=3.03),
        _record(launch_id="firefox-p1", browser="firefox", port=60001, profile_path=profiles_root.joinpath("firefox", "p1"), process_id=404,
                process_created_at=4.04),
    )
    record_paths = _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    relay_termination_calls: list[tuple[int, float, str]] = []
    browser_termination_calls: list[tuple[BrowserName, int, Path | None, int, float, str]] = []
    monkeypatch.setattr(
        agents_browser_lifecycle,
        "terminate_registered_process",
        lambda *, process_id, process_created_at, process_label: relay_termination_calls.append((process_id, process_created_at, process_label)),
    )
    monkeypatch.setattr(
        agents_browser_lifecycle,
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
    assert not record_paths["chrome-p1"].exists()
    assert not record_paths["chrome-z-copied"].exists()
    assert record_paths["chrome-temp"].exists()
    assert record_paths["firefox-p1"].exists()
    assert result.closed == (
        ClosedBrowserLaunch(launch_id="chrome-p1", runtime="detached"),
        ClosedBrowserLaunch(launch_id="chrome-z-copied", runtime="detached"),
    )


def test_close_browser_launch_terminates_matching_detached_record_by_browser_and_port(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=9331, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=101,
                process_created_at=1.01),
        _record(launch_id="chrome-p2", browser="chrome", port=9332, profile_path=profiles_root.joinpath("chrome", "p2"), process_id=202,
                process_created_at=2.02),
        _record(launch_id="firefox-p1", browser="firefox", port=9331, profile_path=profiles_root.joinpath("firefox", "p1"), process_id=303,
                process_created_at=3.03),
        _record(launch_id="chrome-temp", browser="chrome", port=9331, profile_path=tmp_path.joinpath("temp-profiles", "chrome", "port-9331"),
                process_id=404, process_created_at=4.04),
    )
    record_paths = _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    termination_calls: list[int] = []
    monkeypatch.setattr(
        agents_browser_lifecycle,
        "terminate_browser_launch_process",
        lambda *, browser, browser_port, profile_path, process_id, process_created_at, process_label: termination_calls.append(process_id),
    )

    result = agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert termination_calls == [101, 404]
    assert not record_paths["chrome-p1"].exists()
    assert not record_paths["chrome-temp"].exists()
    assert record_paths["chrome-p2"].exists()
    assert record_paths["firefox-p1"].exists()
    assert result.closed == (
        ClosedBrowserLaunch(launch_id="chrome-p1", runtime="detached"),
        ClosedBrowserLaunch(launch_id="chrome-temp", runtime="detached"),
    )


def test_close_all_browser_profile_launches_keeps_failed_record_and_continues_with_later_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=60001, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=101,
                process_created_at=1.01),
        _record(launch_id="chrome-p2", browser="chrome", port=60002, profile_path=profiles_root.joinpath("chrome", "p2"), process_id=202,
                process_created_at=2.02),
    )
    record_paths = _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)
    termination_calls: list[int] = []

    def fail_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        termination_calls.append(process_id)
        if process_id == 101:
            raise RuntimeError(f"Could not terminate {process_label} process {process_id}")

    monkeypatch.setattr(agents_browser_lifecycle, "terminate_browser_launch_process", fail_termination)

    with pytest.raises(RuntimeError, match="Could not terminate chrome browser process 101"):
        agents_browser_close.close_all_browser_profile_launches(browser="chrome")

    assert termination_calls == [101, 202]
    assert record_paths["chrome-p1"].exists()
    assert not record_paths["chrome-p2"].exists()


def test_close_browser_launch_reports_failure_with_browser_and_port_headline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profiles_root = tmp_path.joinpath("browsers-profiles")
    records = (
        _record(launch_id="chrome-p1", browser="chrome", port=9331, profile_path=profiles_root.joinpath("chrome", "p1"), process_id=101,
                process_created_at=1.01),
    )
    record_paths = _install_records(monkeypatch=monkeypatch, tmp_path=tmp_path, profiles_root=profiles_root, records=records)

    def fail_termination(
        *, browser: BrowserName, browser_port: int, profile_path: Path | None, process_id: int, process_created_at: float, process_label: str
    ) -> None:
        raise RuntimeError(f"Could not terminate {process_label} process {process_id}")

    monkeypatch.setattr(agents_browser_lifecycle, "terminate_browser_launch_process", fail_termination)

    with pytest.raises(RuntimeError, match="Could not close the chrome launch on port 9331"):
        agents_browser_close.close_browser_launch(browser="chrome", port=9331)

    assert record_paths["chrome-p1"].exists()
