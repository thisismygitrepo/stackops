from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_LAUNCHES_ROOT, BrowserMultiplexer, BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import find_browser_process_id, registered_process_is_running
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id, browser_profile_label
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchDetails, BrowserWindowHandle


class BrowserWindowHandlePayload(TypedDict):
    multiplexer: BrowserMultiplexer
    session_name: str
    targets: list[str]
    attach_script: str


class BrowserLaunchPayload(TypedDict):
    schema_version: Literal[1]
    launch_id: str
    browser: BrowserName
    profile: str
    host: str
    port: int
    browser_port: int
    profile_path: str | None
    process_id: int
    process_created_at: float
    relay_expected: bool
    relay_process_id: int | None
    relay_process_created_at: float | None
    windows: BrowserWindowHandlePayload | None


@dataclass(frozen=True)
class BrowserLaunchRecord:
    launch_id: str
    browser: BrowserName
    profile: str
    host: str
    port: int
    browser_port: int
    profile_path: Path | None
    process_id: int
    process_created_at: float
    relay_expected: bool
    relay_process_id: int | None
    relay_process_created_at: float | None
    windows: BrowserWindowHandle | None


@dataclass(frozen=True)
class BrowserLaunchStatus:
    launch: BrowserLaunchRecord
    state: Literal["running", "degraded"]
    browser_process_id: int | None
    relay_running: bool


def prepare_browser_launch_registry() -> None:
    try:
        BROWSER_LAUNCHES_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RuntimeError(f"Could not prepare browser launch registry: {error}") from error


def record_browser_launch(
    *,
    details: BrowserLaunchDetails,
    process_id: int,
    process_created_at: float,
    relay_expected: bool,
    relay_process_id: int | None,
    relay_process_created_at: float | None,
    windows: BrowserWindowHandle | None,
) -> BrowserLaunchRecord:
    record = BrowserLaunchRecord(
        launch_id=browser_launch_id(browser=details.browser, profile_path=details.profile_path, port=details.port),
        browser=details.browser,
        profile=browser_profile_label(browser=details.browser, profile_path=details.profile_path, port=details.port),
        host=details.host,
        port=details.port,
        browser_port=details.browser_port,
        profile_path=details.profile_path,
        process_id=process_id,
        process_created_at=process_created_at,
        relay_expected=relay_expected,
        relay_process_id=relay_process_id,
        relay_process_created_at=relay_process_created_at,
        windows=windows,
    )
    payload: BrowserLaunchPayload = {
        "schema_version": 1,
        "launch_id": record.launch_id,
        "browser": record.browser,
        "profile": record.profile,
        "host": record.host,
        "port": record.port,
        "browser_port": record.browser_port,
        "profile_path": None if record.profile_path is None else str(record.profile_path),
        "process_id": record.process_id,
        "process_created_at": record.process_created_at,
        "relay_expected": record.relay_expected,
        "relay_process_id": record.relay_process_id,
        "relay_process_created_at": record.relay_process_created_at,
        "windows": None
        if windows is None
        else {
            "multiplexer": windows.multiplexer,
            "session_name": windows.session_name,
            "targets": list(windows.targets),
            "attach_script": windows.attach_script,
        },
    }
    record_path = BROWSER_LAUNCHES_ROOT.joinpath(f"{record.launch_id}.json")
    temporary_path = BROWSER_LAUNCHES_ROOT.joinpath(f".{record.launch_id}.json.tmp")
    try:
        temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(record_path)
    except OSError as error:
        raise RuntimeError(f"Browser process {record.process_id} is running, but its launch record could not be written: {error}") from error
    return record


def list_browser_launch_record_paths() -> tuple[Path, ...]:
    if not BROWSER_LAUNCHES_ROOT.exists():
        return ()
    try:
        return tuple(sorted(BROWSER_LAUNCHES_ROOT.glob("*.json")))
    except OSError as error:
        raise RuntimeError(f"Could not read browser launch records under {BROWSER_LAUNCHES_ROOT}: {error}") from error


def collect_browser_launch_status() -> tuple[BrowserLaunchStatus, ...]:
    statuses: list[BrowserLaunchStatus] = []
    for record_path in list_browser_launch_record_paths():
        launch = read_browser_launch_record(record_path=record_path)
        browser_process_id = find_browser_process_id(
            browser=launch.browser,
            browser_port=launch.browser_port,
            profile_path=launch.profile_path,
            process_id=launch.process_id,
            process_created_at=launch.process_created_at,
        )
        relay_running = (
            False
            if launch.relay_process_id is None or launch.relay_process_created_at is None
            else registered_process_is_running(process_id=launch.relay_process_id, process_created_at=launch.relay_process_created_at)
        )
        if browser_process_id is None and not relay_running:
            continue
        state: Literal["running", "degraded"] = (
            "running" if browser_process_id is not None and (not launch.relay_expected or relay_running) else "degraded"
        )
        statuses.append(BrowserLaunchStatus(launch=launch, state=state, browser_process_id=browser_process_id, relay_running=relay_running))
    return tuple(statuses)


def read_browser_launch_record(*, record_path: Path) -> BrowserLaunchRecord:
    try:
        payload = cast(BrowserLaunchPayload, json.loads(record_path.read_text(encoding="utf-8")))
        if payload["schema_version"] != 1:
            raise RuntimeError(f"Unsupported browser launch schema in {record_path}")
        windows_payload = payload["windows"]
        return BrowserLaunchRecord(
            launch_id=payload["launch_id"],
            browser=payload["browser"],
            profile=payload["profile"],
            host=payload["host"],
            port=payload["port"],
            browser_port=payload["browser_port"],
            profile_path=None if payload["profile_path"] is None else Path(payload["profile_path"]),
            process_id=payload["process_id"],
            process_created_at=payload["process_created_at"],
            relay_expected=payload["relay_expected"],
            relay_process_id=payload["relay_process_id"],
            relay_process_created_at=payload["relay_process_created_at"],
            windows=None
            if windows_payload is None
            else BrowserWindowHandle(
                multiplexer=windows_payload["multiplexer"],
                session_name=windows_payload["session_name"],
                targets=tuple(windows_payload["targets"]),
                attach_script=windows_payload["attach_script"],
            ),
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Invalid browser launch record {record_path}: {error}") from error
