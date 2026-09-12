import multiprocessing
import signal
import socket
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

import psutil
import pytest

from stackops.utils.dashboards import lifecycle
from stackops.utils.dashboards.ownership import DashboardOwner, owner_is_healthy, read_owner


class LaunchArguments(TypedDict):
    command: tuple[str, ...]
    port: int
    identity: str
    cwd: Path
    environment: dict[str, str]
    health_path: str
    state_dir: Path


@pytest.fixture()
def launch(tmp_path: Path) -> LaunchArguments:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return LaunchArguments(
        command=(sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"),
        port=port, identity="test dashboard", cwd=tmp_path, environment={},
        health_path="/", state_dir=tmp_path / "owners",
    )


def start_manager(launch: LaunchArguments) -> multiprocessing.Process:
    manager = multiprocessing.Process(target=lifecycle.run_dashboard, kwargs=launch)
    manager.start()
    return manager


def wait_for_owner(launch: LaunchArguments) -> DashboardOwner:
    deadline = time.monotonic() + 10
    owner_path = launch["state_dir"] / f"""{launch['port']}.json"""
    while time.monotonic() < deadline:
        owner = read_owner(owner_path)
        if owner is not None and owner_is_healthy(owner, launch["port"], launch["health_path"]):
            return owner
        time.sleep(0.05)
    raise AssertionError("Dashboard did not become healthy")


@pytest.fixture()
def managed(launch: LaunchArguments) -> Iterator[DashboardOwner]:
    manager = start_manager(launch)
    try:
        yield wait_for_owner(launch)
    finally:
        manager.terminate()
        manager.join(timeout=10)
        assert not manager.is_alive()


def test_matching_launch_reuses_owner(launch: LaunchArguments, managed: DashboardOwner, capsys: pytest.CaptureFixture[str]) -> None:
    assert lifecycle.run_dashboard(**launch) == 0
    assert f"""Reusing test dashboard (PID {managed.pid})""" in capsys.readouterr().out
    assert owner_is_healthy(managed, launch["port"], "/")


def test_concurrent_launches_create_one_server(launch: LaunchArguments) -> None:
    managers = [start_manager(launch) for _ in range(4)]
    try:
        owner = wait_for_owner(launch)
        deadline = time.monotonic() + 10
        while sum(manager.is_alive() for manager in managers) > 1 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert sum(manager.is_alive() for manager in managers) == 1
        assert owner_is_healthy(owner, launch["port"], "/")
        assert all(manager.exitcode in (None, 0) for manager in managers)
    finally:
        for manager in managers:
            if manager.is_alive():
                manager.terminate()
            manager.join(timeout=10)
            assert not manager.is_alive()


def test_different_launch_leaves_owner_running(launch: LaunchArguments, managed: DashboardOwner) -> None:
    launch["identity"] = "another dashboard"
    with pytest.raises(RuntimeError, match="different managed dashboard"):
        lifecycle.run_dashboard(**launch)
    assert owner_is_healthy(managed, launch["port"], "/")


def test_unhealthy_owner_is_not_replaced(launch: LaunchArguments, managed: DashboardOwner) -> None:
    launch["health_path"] = "/missing-health"
    with pytest.raises(RuntimeError, match="unhealthy"):
        lifecycle.run_dashboard(**launch)
    assert psutil.pid_exists(managed.pid)


@pytest.mark.parametrize("record_state", ["missing", "reused_pid"])
def test_unmanaged_listener_is_preserved(launch: LaunchArguments, managed: DashboardOwner, record_state: str) -> None:
    owner_path = launch["state_dir"] / f"""{launch['port']}.json"""
    if record_state == "missing":
        owner_path.unlink()
    else:
        stale = managed.model_copy(update={"created_at": managed.created_at - 1})
        owner_path.write_text(stale.model_dump_json(), encoding="utf-8")
    with pytest.raises(RuntimeError, match="unmanaged listener"):
        lifecycle.run_dashboard(**launch)
    assert owner_is_healthy(managed, launch["port"], "/")


def test_dead_record_can_be_replaced(launch: LaunchArguments) -> None:
    launch["state_dir"].mkdir()
    owner_path = launch["state_dir"] / f"""{launch['port']}.json"""
    stale = DashboardOwner(fingerprint="old", pid=psutil.Process().pid, created_at=0.0)
    owner_path.write_text(stale.model_dump_json(), encoding="utf-8")
    manager = start_manager(launch)
    try:
        owner = wait_for_owner(launch)
        assert owner != stale
    finally:
        manager.terminate()
        manager.join(timeout=10)
    assert not owner_path.exists()


def test_startup_failure_removes_record(launch: LaunchArguments) -> None:
    launch["command"] = (sys.executable, "-c", "import sys; sys.exit(7)")
    with pytest.raises(RuntimeError, match="exited with status 7"):
        lifecycle.run_dashboard(**launch)
    assert not (launch["state_dir"] / f"""{launch['port']}.json""").exists()


def test_startup_timeout_stops_only_new_child(launch: LaunchArguments, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lifecycle, "STARTUP_TIMEOUT_SECONDS", 0.2)
    launch["command"] = (sys.executable, "-c", "import time; time.sleep(60)")
    initial_children = {process.pid for process in psutil.Process().children()}
    with pytest.raises(RuntimeError, match="did not become healthy"):
        lifecycle.run_dashboard(**launch)
    assert {process.pid for process in psutil.Process().children()} == initial_children
    assert not (launch["state_dir"] / f"""{launch['port']}.json""").exists()


def test_supervisor_termination_cleans_owned_child(launch: LaunchArguments) -> None:
    manager = start_manager(launch)
    owner = wait_for_owner(launch)
    assert manager.pid is not None
    psutil.Process(manager.pid).send_signal(signal.SIGTERM)
    manager.join(timeout=10)
    assert not manager.is_alive()
    assert not psutil.pid_exists(owner.pid)
    assert not (launch["state_dir"] / f"""{launch['port']}.json""").exists()


def test_child_exit_status_is_returned(launch: LaunchArguments, monkeypatch: pytest.MonkeyPatch) -> None:
    launch["command"] = (sys.executable, "-c", "import time; time.sleep(0.1); raise SystemExit(9)")
    monkeypatch.setattr(lifecycle, "owner_is_healthy", lambda owner, port, health_path: True)
    assert lifecycle.run_dashboard(**launch) == 9


def test_credentials_are_not_saved(launch: LaunchArguments) -> None:
    launch["environment"] = {"PGWEB_DATABASE_URL": "postgres://test:fake-password@localhost/db"}
    manager = start_manager(launch)
    try:
        wait_for_owner(launch)
        record = (launch["state_dir"] / f"""{launch['port']}.json""").read_text(encoding="utf-8")
        assert "fake-password" not in record
        assert "PGWEB_DATABASE_URL" not in record
    finally:
        manager.terminate()
        manager.join(timeout=10)
