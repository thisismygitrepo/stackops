import subprocess

from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_common import (
    require_tmux,
    run_optional_tmux_command,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import (
    STACKOPS_BROWSER_TMUX_SESSION_NAME,
    TMUX_FIELD_SEPARATOR,
    BrowserTmuxMetadata,
    BrowserTmuxPaneStatus,
    RawTmuxPane,
)


def collect_browser_tmux_status() -> tuple[BrowserTmuxPaneStatus, ...]:
    require_tmux()
    metadata_by_window_id: dict[str, BrowserTmuxMetadata] = {}
    rows: list[BrowserTmuxPaneStatus] = []
    for pane in _list_browser_tmux_panes():
        metadata = metadata_by_window_id.get(pane.window_id)
        if metadata is None:
            metadata = _read_window_metadata(window_id=pane.window_id)
            metadata_by_window_id[pane.window_id] = metadata
        if metadata.launch_id == "-":
            continue
        rows.append(
            BrowserTmuxPaneStatus(
                session_name=pane.session_name,
                window_index=pane.window_index,
                window_id=pane.window_id,
                window_name=pane.window_name,
                pane_index=pane.pane_index,
                pane_id=pane.pane_id,
                pane_pid=pane.pane_pid,
                pane_current_command=pane.pane_current_command,
                pane_dead=pane.pane_dead,
                pane_current_path=pane.pane_current_path,
                metadata=metadata,
            )
        )
    return tuple(rows)


def _read_window_metadata(*, window_id: str) -> BrowserTmuxMetadata:
    return BrowserTmuxMetadata(
        launch_id=_read_window_option(window_id=window_id, option="@stackops_browser_launch_id"),
        role=_read_window_option(window_id=window_id, option="@stackops_browser_role"),
        browser=_read_window_option(window_id=window_id, option="@stackops_browser"),
        profile=_read_window_option(window_id=window_id, option="@stackops_browser_profile"),
        profile_path=_read_window_option(window_id=window_id, option="@stackops_browser_profile_path"),
        host=_read_window_option(window_id=window_id, option="@stackops_browser_host"),
        port=_read_window_option(window_id=window_id, option="@stackops_browser_port"),
        browser_port=_read_window_option(window_id=window_id, option="@stackops_browser_browser_port"),
        lan=_read_window_option(window_id=window_id, option="@stackops_browser_lan"),
        prompt_path=_read_window_option(window_id=window_id, option="@stackops_browser_prompt_path"),
    )


def _read_window_option(*, window_id: str, option: str) -> str:
    result = subprocess.run(
        ("tmux", "show-window-options", "-qv", "-t", window_id, option),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "-"
    value = result.stdout.strip()
    if value == "":
        return "-"
    return value


def _list_browser_tmux_panes() -> tuple[RawTmuxPane, ...]:
    fields = (
        "#{session_name}",
        "#{window_index}",
        "#{window_id}",
        "#{window_name}",
        "#{pane_index}",
        "#{pane_id}",
        "#{pane_pid}",
        "#{pane_current_command}",
        "#{pane_dead}",
        "#{pane_current_path}",
    )
    result = run_optional_tmux_command(command=("tmux", "list-panes", "-s", "-t", STACKOPS_BROWSER_TMUX_SESSION_NAME, "-F", TMUX_FIELD_SEPARATOR.join(fields)))
    if result is None:
        return ()
    return tuple(_parse_pane_line(line=line, field_count=len(fields)) for line in result.stdout.splitlines() if line.strip())


def _parse_pane_line(*, line: str, field_count: int) -> RawTmuxPane:
    parts = line.split(TMUX_FIELD_SEPARATOR)
    if len(parts) != field_count:
        raise RuntimeError(f"""Unexpected tmux list-panes output: {line}""")
    return RawTmuxPane(
        session_name=parts[0],
        window_index=parts[1],
        window_id=parts[2],
        window_name=parts[3],
        pane_index=parts[4],
        pane_id=parts[5],
        pane_pid=parts[6],
        pane_current_command=parts[7],
        pane_dead=parts[8] == "1",
        pane_current_path=parts[9],
    )
