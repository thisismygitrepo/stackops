import shlex
import shutil

from stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux import build_mount_pane_command
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend import attach_session_script
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    free_workspace_number,
    list_session_entries,
    list_window_entries,
    list_workspace_entries,
    run_tuios,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands import close_window, launch_tab, launch_window
from stackops.utils.schemas.layouts.layout_types import PaneConfig

SERVICE_PANE_NAME = "service"


def launch_tuios_mount_session(
    mount_commands: dict[str, str], mount_locations: dict[str, str], session_name: str, unmounted_clouds: set[str]
) -> str:
    if shutil.which("tuios") is None:
        raise ValueError("tuios is not installed or not on PATH.")
    if any(session.name == session_name and session.saved for session in list_session_entries()):
        run_tuios(["start-server"])
    bootstrap_window_ids: list[str] = []
    if not any(session.name == session_name and not session.saved for session in list_session_entries()):
        run_tuios(["new", "--detach", "--", session_name])
        bootstrap_window_ids = [window.window_id for window in list_window_entries(session_name)]

    workspace_numbers: dict[str, int] = {}
    for cloud_name, mount_command in mount_commands.items():
        mount_location = mount_locations[cloud_name]
        service_pane: PaneConfig = {"paneName": SERVICE_PANE_NAME, "startDir": "~", "command": build_mount_pane_command(mount_command=mount_command)}
        named_workspace = next((workspace.number for workspace in list_workspace_entries(session_name) if workspace.name == cloud_name), None)
        workspace_number = (
            named_workspace if named_workspace is not None
            else free_workspace_number(session_name=session_name, ignored_window_ids=frozenset(bootstrap_window_ids))
        )
        workspace_windows = [
            window for window in list_window_entries(session_name)
            if window.workspace == workspace_number and window.window_id not in bootstrap_window_ids
        ]
        if not workspace_windows:
            launch_tab(
                session_name=session_name,
                tab={
                    "tabName": cloud_name,
                    "panes": [
                        service_pane,
                        {"paneName": "about", "startDir": "~", "command": f"""rclone about {shlex.quote(f'{cloud_name}:')}"""},
                        {"paneName": "explorer", "startDir": "~", "command": f"""yazi {shlex.quote(mount_location)}"""},
                        {"paneName": "monitor", "startDir": "~", "command": "btm --default_widget_type net --expanded"},
                        {"paneName": "shell", "startDir": mount_location, "command": "pwd"},
                    ],
                },
                exit_mode="backToShell",
                workspace=workspace_number,
            )
        else:
            service_windows = [window for window in workspace_windows if window.display_name == SERVICE_PANE_NAME]
            if cloud_name in unmounted_clouds and all(window.at_prompt is True and window.command_seq > 0 for window in service_windows):
                launch_window(session_name=session_name, pane=service_pane, exit_mode="backToShell", workspace=workspace_number)
                for window in service_windows:
                    close_window(session_name=session_name, window_id=window.window_id)
        workspace_numbers[cloud_name] = workspace_number

    for window_id in bootstrap_window_ids:
        close_window(session_name=session_name, window_id=window_id)
    first_workspace = workspace_numbers[next(iter(mount_commands))]
    return f"""tuios select-workspace {first_workspace} --session {shlex.quote(session_name)} &&
{attach_session_script(session_name)}"""
