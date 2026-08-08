from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Literal, cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_DETACHED_LAUNCHES_ROOT,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    find_browser_process_id,
    registered_process_is_running,
    terminate_registered_process,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_status import (
    collect_detached_browser_status,
    read_detached_browser_launch,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import (
    collect_browser_tmux_status,
    prune_dead_browser_tmux_launches,
)


@dataclass(frozen=True)
class ActiveBrowserEndpoint:
    browser: BrowserName
    profile_path: Path | None
    port: int
    browser_port: int
    lan: bool
    process_id: int
    process_created_at: float | None
    owner: Literal["tmux", "detached"]
    relay_running: bool


def prepare_browser_launch_state() -> None:
    if shutil.which("tmux") is not None:
        prune_dead_browser_tmux_launches()
    if not BROWSER_DETACHED_LAUNCHES_ROOT.exists():
        return
    for record_path in sorted(BROWSER_DETACHED_LAUNCHES_ROOT.glob("*.json")):
        launch = read_detached_browser_launch(record_path=record_path)
        browser_process_id = find_browser_process_id(
            browser=launch.browser,
            browser_port=launch.browser_port,
            profile_path=launch.profile_path,
            process_id=launch.process_id,
            process_created_at=launch.process_created_at,
        )
        if browser_process_id is not None:
            continue
        relay_running = (
            launch.relay_process_id is not None
            and launch.relay_process_created_at is not None
            and registered_process_is_running(
                process_id=launch.relay_process_id,
                process_created_at=launch.relay_process_created_at,
            )
        )
        if relay_running and launch.relay_process_id is not None and launch.relay_process_created_at is not None:
            terminate_registered_process(
                process_id=launch.relay_process_id,
                process_created_at=launch.relay_process_created_at,
                process_label="browser endpoint LAN relay",
            )
        try:
            record_path.unlink()
        except OSError as error:
            raise RuntimeError(f"Could not remove stale detached browser record {record_path}: {error}") from error


def collect_active_browser_endpoints() -> tuple[ActiveBrowserEndpoint, ...]:
    endpoints: list[ActiveBrowserEndpoint] = []
    tmux_rows = collect_browser_tmux_status() if shutil.which("tmux") is not None else ()
    for row in tmux_rows:
        if row.metadata.role != "endpoint" or row.pane_dead:
            continue
        relay_running = any(
            candidate.metadata.launch_id == row.metadata.launch_id
            and candidate.metadata.role == "relay"
            and not candidate.pane_dead
            for candidate in tmux_rows
        )
        endpoints.append(
            ActiveBrowserEndpoint(
                browser=cast(BrowserName, row.metadata.browser),
                profile_path=None if row.metadata.profile_path == "-" else Path(row.metadata.profile_path),
                port=int(row.metadata.port),
                browser_port=int(row.metadata.browser_port),
                lan=row.metadata.lan == "yes",
                process_id=int(row.pane_pid),
                process_created_at=None,
                owner="tmux",
                relay_running=relay_running,
            )
        )
    for status in collect_detached_browser_status():
        if status.browser_process_id is None:
            continue
        launch = status.launch
        endpoints.append(
            ActiveBrowserEndpoint(
                browser=launch.browser,
                profile_path=launch.profile_path,
                port=launch.port,
                browser_port=launch.browser_port,
                lan=launch.relay_expected,
                process_id=status.browser_process_id,
                process_created_at=launch.process_created_at,
                owner="detached",
                relay_running=status.relay_running,
            )
        )
    return tuple(endpoints)
