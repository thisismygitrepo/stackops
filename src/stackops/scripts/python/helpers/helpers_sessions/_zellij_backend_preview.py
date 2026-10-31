from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry, SessionEntry, TabEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_pane_entries
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_commands import original_command, original_start_dir


def pane_preview(session_name: str, pane: PaneEntry) -> str:
    return "\n".join([
        "backend: zellij",
        f"""session: {session_name}""",
        f"""tab: {pane.tab_name} [{pane.tab_id}]""",
        f"""pane: {pane.title} [{pane.pane_id}]""",
        f"""cwd: {pane.cwd or original_start_dir(pane.terminal_command)}""",
        f"""command: {original_command(pane.command or pane.terminal_command)}""",
        f"""exited: {pane.exited}""",
        f"""exit code: {pane.exit_status}""",
    ])


def tab_label(session_name: str, tab: TabEntry) -> str:
    focused = " *" if tab.active else ""
    return f"""{session_name} / tab {tab.position + 1}: {tab.name} [{tab.tab_id}]{focused}"""


def pane_label(session_name: str, pane: PaneEntry) -> str:
    focused = " *" if pane.focused else ""
    return f"""{session_name} / tab {pane.tab_position + 1}: {pane.tab_name} / {pane.title} [{pane.pane_id}]{focused}"""


def session_preview(session: SessionEntry) -> str:
    status = "exited (attach to resurrect)" if session.exited else "running"
    lines = ["backend: zellij", f"""session: {session.name}""", f"""status: {status}"""]
    if not session.exited:
        lines.extend(
            f"""{pane_label(session.name, pane)}\n  {original_command(pane.command or pane.terminal_command)}\n  cwd: {pane.cwd or original_start_dir(pane.terminal_command)}"""
            for pane in list_pane_entries(session.name)
        )
    return "\n".join(lines)
