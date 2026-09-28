from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import SessionEntry, WindowEntry
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_window_entries


def window_label(session_name: str, window: WindowEntry) -> str:
    focused = " *" if window.focused else ""
    return f"""{session_name} / workspace {window.workspace} / {window.index}:{window.display_name} [{window.window_id[:8]}]{focused}"""


def window_preview(session_name: str, window: WindowEntry) -> str:
    lines = [
        "backend: tuios",
        f"""session: {session_name}""",
        f"""workspace: {window.workspace}""",
        f"""window: {window.display_name}""",
        f"""window id: {window.window_id}""",
        f"""focused: {'yes' if window.focused else 'no'}""",
        f"""cwd: {window.cwd}""",
        f"""agent state: {window.agent_state}""",
    ]
    if window.running_command:
        lines.append(f"""command: {window.running_command}""")
    return "\n".join(lines)


def session_preview(session: SessionEntry) -> str:
    status = "saved" if session.saved else "attached" if session.attached else "detached"
    lines = ["backend: tuios", f"""session: {session.name}""", f"""status: {status}""", f"""windows: {session.window_count}"""]
    if not session.saved:
        lines.extend(window_label(session.name, window) for window in list_window_entries(session.name))
    return "\n".join(lines)
