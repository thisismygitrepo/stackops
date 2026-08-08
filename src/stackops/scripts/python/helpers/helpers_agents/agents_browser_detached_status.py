from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_DETACHED_LAUNCHES_ROOT, BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import find_browser_process_id, registered_process_is_running
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id, browser_profile_label
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import DetachedBrowserLaunchResult


class DetachedBrowserLaunchPayload(TypedDict):
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


@dataclass(frozen=True)
class DetachedBrowserLaunchRecord:
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


@dataclass(frozen=True)
class DetachedBrowserStatus:
    launch: DetachedBrowserLaunchRecord
    state: Literal["running", "degraded"]
    browser_process_id: int | None
    relay_running: bool


def prepare_detached_browser_registry() -> None:
    try:
        BROWSER_DETACHED_LAUNCHES_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RuntimeError(f"Could not prepare detached browser status registry: {error}") from error


def record_detached_browser_launch(
    *, result: DetachedBrowserLaunchResult, process_created_at: float, relay_expected: bool, relay_process_created_at: float | None
) -> None:
    launch_id = browser_launch_id(browser=result.browser, profile_path=result.profile_path, port=result.port)
    record = DetachedBrowserLaunchRecord(
        launch_id=launch_id,
        browser=result.browser,
        profile=browser_profile_label(browser=result.browser, profile_path=result.profile_path, port=result.port),
        host=result.host,
        port=result.port,
        browser_port=result.browser_port,
        profile_path=result.profile_path,
        process_id=result.process_id,
        process_created_at=process_created_at,
        relay_expected=relay_expected,
        relay_process_id=result.relay_process_id,
        relay_process_created_at=relay_process_created_at,
    )
    payload: DetachedBrowserLaunchPayload = {
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
    }
    record_path = BROWSER_DETACHED_LAUNCHES_ROOT.joinpath(f"{record.launch_id}.json")
    temporary_path = BROWSER_DETACHED_LAUNCHES_ROOT.joinpath(f".{record.launch_id}.json.tmp")
    try:
        temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(record_path)
    except OSError as error:
        raise RuntimeError(f"Browser process {record.process_id} is running, but its detached status record could not be written: {error}") from error


def collect_detached_browser_status() -> tuple[DetachedBrowserStatus, ...]:
    if not BROWSER_DETACHED_LAUNCHES_ROOT.exists():
        return ()
    statuses: list[DetachedBrowserStatus] = []
    for record_path in sorted(BROWSER_DETACHED_LAUNCHES_ROOT.glob("*.json")):
        launch = _read_detached_browser_launch(record_path=record_path)
        browser_process_id = find_browser_process_id(
            launch_id=launch.launch_id,
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
        statuses.append(DetachedBrowserStatus(launch=launch, state=state, browser_process_id=browser_process_id, relay_running=relay_running))
    return tuple(statuses)


def _read_detached_browser_launch(*, record_path: Path) -> DetachedBrowserLaunchRecord:
    try:
        payload = cast(DetachedBrowserLaunchPayload, json.loads(record_path.read_text(encoding="utf-8")))
        if payload["schema_version"] != 1:
            raise RuntimeError(f"Unsupported detached browser launch schema in {record_path}")
        return DetachedBrowserLaunchRecord(
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
        )
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Invalid detached browser status record {record_path}: {error}") from error
