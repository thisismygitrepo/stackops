from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    collect_selected_option_scripts,
    interactive_choose_with_preview,
    quote,
)
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_idle import build_idle_kill_script_for_sessions
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_preview import session_preview, window_label, window_preview
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    kill_window_command,
    list_session_entries,
    list_window_entries,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget


def choose_kill_target(
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    if idle and window:
        return "error", "--idle cannot be used together with --window.", []
    try:
        sessions = [session for session in list_session_entries() if not session.saved]
        if name is not None:
            sessions = [session for session in sessions if session.name == name]
        if not sessions:
            detail = f"""No running TUIOS session named '{name}' is available.""" if name else "No running TUIOS sessions are available."
            return "error", detail, []
        if idle:
            selected_names = [session.name for session in sessions]
            if not kill_all and name is None:
                selection = interactive_choose_with_preview(
                    msg="Choose a TUIOS session to clean idle windows:",
                    options_to_preview_mapping={session.name: session_preview(session) for session in sessions},
                )
                if selection is None:
                    return "error", "No TUIOS session selected.", []
                if selection not in selected_names:
                    return "error", f"""Unknown TUIOS session selected: {selection}""", []
                selected_names = [selection]
            script, killed_targets = build_idle_kill_script_for_sessions(selected_names)
            if not script:
                return "error", "No idle-shell TUIOS windows are available to kill.", []
            return "run_script", script, killed_targets
        if kill_all or name is not None:
            scripts = [f"""tuios kill-session -- {quote(session.name)}""" for session in sessions]
            return "run_script", "\n".join(scripts), []
        scripts_by_label: dict[str, str] = {}
        previews: dict[str, str] = {}
        parent_labels: dict[str, tuple[str, ...]] = {}
        for session in sessions:
            label = f"""session: {session.name}"""
            scripts_by_label[label] = f"""tuios kill-session -- {quote(session.name)}"""
            previews[label] = session_preview(session)
            parent_labels[label] = ()
            if window:
                for entry in list_window_entries(session.name):
                    target_label = window_label(session.name, entry)
                    scripts_by_label[target_label] = " ".join(
                        quote(argument) for argument in kill_window_command(session.name, entry.window_id)
                    )
                    previews[target_label] = window_preview(session.name, entry)
                    parent_labels[target_label] = (label,)
        selections = interactive_choose_with_preview(
            msg="Choose TUIOS sessions or windows to kill:" if window else "Choose TUIOS sessions to kill:",
            options_to_preview_mapping=previews,
            multi=True,
        )
    except ValueError as error:
        return "error", str(error), []
    if not selections:
        return "error", "No TUIOS target selected.", []
    scripts, unknown_selection = collect_selected_option_scripts(
        selections=selections, options_to_script=scripts_by_label, option_parent_labels=parent_labels,
    )
    if unknown_selection is not None:
        return "error", f"""Unknown TUIOS target selected: {unknown_selection}""", []
    return "run_script", "\n".join(scripts), []
