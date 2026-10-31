import os
from shlex import join as shell_command

from stackops.scripts.python.helpers.helpers_sessions._attach_common import collect_selected_option_scripts, interactive_choose_with_preview
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle import build_idle_kill_script_for_sessions
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_preview import pane_label, pane_preview, session_preview, tab_label
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_pane_entries, list_session_entries, list_tab_entries
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget


def choose_kill_target(name: str | None, kill_all: bool, idle: bool, window: bool, delete: bool) -> tuple[str, str | None, list[KilledTarget]]:
    if idle and window:
        return "error", "--idle cannot be used together with --window.", []
    if delete and (idle or window):
        return "error", "--delete cannot be used with --idle or --window.", []
    try:
        sessions = [session for session in list_session_entries() if session.exited == delete]
        if name is not None:
            sessions = [session for session in sessions if session.name == name]
        sessions.sort(key=lambda session: session.name == os.environ.get("ZELLIJ_SESSION_NAME"))
        if not sessions:
            status = "exited" if delete else "running"
            detail = f"""No {status} Zellij session named '{name}' is available.""" if name else f"""No {status} Zellij sessions are available."""
            return "error", detail, []
        if idle:
            selected_names = [session.name for session in sessions]
            if not kill_all and name is None:
                selection = interactive_choose_with_preview(
                    msg="Choose a Zellij session to clean idle panes:",
                    options_to_preview_mapping={session.name: session_preview(session) for session in sessions},
                    multi=False,
                )
                if selection is None:
                    return "error", "No Zellij session selected.", []
                if selection not in selected_names:
                    return "error", f"""Unknown Zellij session selected: {selection}""", []
                selected_names = [selection]
            script, killed_targets = build_idle_kill_script_for_sessions(selected_names)
            if not script:
                return "error", "No idle-shell Zellij panes are available to kill.", []
            return "run_script", script, killed_targets
        session_action = "delete-session" if delete else "kill-session"
        if kill_all or name is not None:
            scripts = [shell_command(["zellij", session_action, "--", session.name]) for session in sessions]
            return "run_script", "\n".join(scripts), []
        scripts_by_label: dict[str, str] = {}
        previews: dict[str, str] = {}
        parent_labels: dict[str, tuple[str, ...]] = {}
        for session in sessions:
            session_label = f"""session: {session.name}"""
            scripts_by_label[session_label] = shell_command(["zellij", session_action, "--", session.name])
            previews[session_label] = session_preview(session)
            parent_labels[session_label] = ()
            if window:
                panes = list_pane_entries(session.name)
                tabs = list_tab_entries(session.name)
                tab_labels = {tab.tab_id: tab_label(session.name, tab) for tab in tabs}
                for tab in tabs:
                    label = tab_labels[tab.tab_id]
                    scripts_by_label[label] = shell_command(["zellij", "--session", session.name, "action", "close-tab-by-id", str(tab.tab_id)])
                    previews[label] = "\n\n".join(pane_preview(session.name, pane) for pane in panes if pane.tab_id == tab.tab_id)
                    parent_labels[label] = (session_label,)
                for pane in panes:
                    label = pane_label(session.name, pane)
                    scripts_by_label[label] = shell_command(["zellij", "--session", session.name, "action", "close-pane", "--pane-id", pane.pane_id])
                    previews[label] = pane_preview(session.name, pane)
                    tab_parent = tab_labels.get(pane.tab_id)
                    parent_labels[label] = (session_label, tab_parent) if tab_parent is not None else (session_label,)
        selections = interactive_choose_with_preview(
            msg="Choose exited Zellij sessions to delete:" if delete else "Choose Zellij targets to kill:",
            options_to_preview_mapping=previews,
            multi=True,
        )
    except ValueError as error:
        return "error", str(error), []
    if not selections:
        return "error", "No Zellij target selected.", []
    scripts, unknown_selection = collect_selected_option_scripts(
        selections=selections, options_to_script=scripts_by_label, option_parent_labels=parent_labels,
    )
    if unknown_selection is not None:
        return "error", f"""Unknown Zellij target selected: {unknown_selection}""", []
    current_session = os.environ.get("ZELLIJ_SESSION_NAME")
    if current_session:
        current_kill = shell_command(["zellij", "kill-session", "--", current_session])
        scripts.sort(key=lambda script: script == current_kill)
    return "run_script", "\n".join(scripts), []
