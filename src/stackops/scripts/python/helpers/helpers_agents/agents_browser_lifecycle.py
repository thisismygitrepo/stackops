from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    find_browser_process_id,
    terminate_browser_launch_process,
    terminate_registered_process,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_hosts import close_browser_windows
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import (
    BrowserLaunchRecord,
    list_browser_launch_record_paths,
    read_browser_launch_record,
)


def prepare_browser_launch_state() -> None:
    for record_path in list_browser_launch_record_paths():
        launch = read_browser_launch_record(record_path=record_path)
        browser_process_id = find_browser_process_id(
            browser=launch.browser,
            browser_port=launch.browser_port,
            profile_path=launch.profile_path,
            process_id=launch.process_id,
            process_created_at=launch.process_created_at,
        )
        if browser_process_id is None:
            retire_browser_launch(launch=launch, record_path=record_path)


def retire_browser_launch(*, launch: BrowserLaunchRecord, record_path: Path) -> None:
    if (launch.relay_process_id is None) != (launch.relay_process_created_at is None):
        raise RuntimeError("relay process identity is incomplete")
    if launch.relay_process_id is not None and launch.relay_process_created_at is not None:
        terminate_registered_process(
            process_id=launch.relay_process_id, process_created_at=launch.relay_process_created_at, process_label="browser endpoint LAN relay"
        )
    terminate_browser_launch_process(
        browser=launch.browser,
        browser_port=launch.browser_port,
        profile_path=launch.profile_path,
        process_id=launch.process_id,
        process_created_at=launch.process_created_at,
        process_label=f"{launch.browser} browser",
    )
    if launch.windows is not None:
        close_browser_windows(handle=launch.windows)
    try:
        record_path.unlink()
    except OSError as error:
        raise RuntimeError(f"Could not remove browser launch record {record_path}: {error}") from error
