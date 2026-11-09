from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from rich.console import Console

from stackops.scripts.python.helpers.helpers_network import warp_connect
from stackops.scripts.python.helpers.helpers_network.warp_status import WarpRejection, WarpStatus

CONNECTED = WarpStatus(state="connected", detail="NetworkHealthy")
CONNECTING = WarpStatus(state="connecting", detail=None)
DISCONNECTED = WarpStatus(state="disconnected", detail="ManualDisconnection")
MISSING = WarpStatus(state="registration_missing", detail="DaemonStartup")
DAEMON_DOWN = WarpStatus(state="daemon_down", detail="FailedToConnectToDaemon: gone")


@dataclass(slots=True)
class FakeWarp:
    status: WarpStatus
    daemon_status: WarpStatus
    stale_registration: bool
    registration_rejection: WarpRejection | None
    loads_stored_registration: bool
    actions: list[tuple[str, ...]] = field(default_factory=list)

    def read_status(self) -> WarpStatus:
        current = self.status
        if current == CONNECTING:
            self.status = CONNECTED
        return current

    def request_action(self, arguments: tuple[str, ...]) -> WarpRejection | None:
        self.actions.append(arguments)
        match arguments:
            case ("connect",):
                if self.status != MISSING:
                    self.status = CONNECTING
            case ("registration", "new") if self.stale_registration:
                if self.loads_stored_registration:
                    self.status = DISCONNECTED
                return WarpRejection(code="RegistrationExists", message="Old registration is still around.")
            case ("registration", "new") if self.registration_rejection is not None:
                return self.registration_rejection
            case ("registration", "new"):
                self.status = DISCONNECTED
            case ("registration", "delete"):
                self.stale_registration = False
            case _:
                raise AssertionError(arguments)
        return None

    def start_daemon(self, console: Console) -> None:
        _ = console
        self.actions.append(("start-daemon",))
        self.status = self.daemon_status


DriveWarp = Callable[[FakeWarp, float], warp_connect.WarpConnected | warp_connect.WarpFailure]


@pytest.fixture
def drive(monkeypatch: pytest.MonkeyPatch) -> DriveWarp:
    def run(fake: FakeWarp, timeout_seconds: float) -> warp_connect.WarpConnected | warp_connect.WarpFailure:
        monkeypatch.setattr(warp_connect, "read_warp_status", fake.read_status)
        monkeypatch.setattr(warp_connect, "request_warp_action", fake.request_action)
        monkeypatch.setattr(warp_connect, "_start_daemon", fake.start_daemon)
        return warp_connect._drive_to_connected(timeout_seconds=timeout_seconds, wait_seconds=0.0, console=Console(quiet=True))

    return run


def make_fake(status: WarpStatus) -> FakeWarp:
    return FakeWarp(status=status, daemon_status=DISCONNECTED, stale_registration=False, registration_rejection=None, loads_stored_registration=False)


def test_already_connected_issues_no_action(drive: DriveWarp) -> None:
    fake = make_fake(CONNECTED)
    assert drive(fake, 1.0) == warp_connect.WarpConnected(status=CONNECTED)
    assert fake.actions == []


def test_disconnected_requests_connection(drive: DriveWarp) -> None:
    fake = make_fake(DISCONNECTED)
    assert isinstance(drive(fake, 1.0), warp_connect.WarpConnected)
    assert fake.actions == [("connect",)]


def test_missing_registration_registers_then_connects(drive: DriveWarp) -> None:
    fake = make_fake(MISSING)
    assert isinstance(drive(fake, 1.0), warp_connect.WarpConnected)
    assert fake.actions == [("registration", "new"), ("connect",)]


def test_stale_registration_is_replaced_then_connects(drive: DriveWarp) -> None:
    fake = make_fake(MISSING)
    fake.stale_registration = True
    assert isinstance(drive(fake, 1.0), warp_connect.WarpConnected)
    assert fake.actions == [("registration", "new"), ("registration", "delete"), ("registration", "new"), ("connect",)]


def test_registration_loading_after_daemon_start_is_not_deleted(drive: DriveWarp) -> None:
    fake = make_fake(MISSING)
    fake.stale_registration = True
    fake.loads_stored_registration = True
    assert isinstance(drive(fake, 1.0), warp_connect.WarpConnected)
    assert ("registration", "delete") not in fake.actions


def test_daemon_down_starts_service_then_recovers_registration(drive: DriveWarp) -> None:
    fake = make_fake(DAEMON_DOWN)
    fake.daemon_status = MISSING
    assert isinstance(drive(fake, 1.0), warp_connect.WarpConnected)
    assert fake.actions == [("start-daemon",), ("registration", "new"), ("connect",)]


def test_registration_api_failure_stops_without_deleting(drive: DriveWarp) -> None:
    fake = make_fake(MISSING)
    fake.registration_rejection = WarpRejection(code="ApiError", message="Failed to communicate with the WARP API.")
    result = drive(fake, 1.0)
    assert isinstance(result, warp_connect.WarpFailure)
    assert result.reason == "registration_failed"
    assert fake.actions == [("registration", "new")]


def test_status_that_never_connects_times_out(drive: DriveWarp) -> None:
    fake = make_fake(WarpStatus(state="unable", detail="NoNetwork"))
    result = drive(fake, 0.0)
    assert isinstance(result, warp_connect.WarpFailure)
    assert result.reason == "connection_timeout"
    assert "NoNetwork" in result.message
