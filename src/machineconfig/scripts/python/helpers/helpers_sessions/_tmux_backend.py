from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend_options import (
    attach_script_from_name,
    build_window_target_options,
    new_session_script,
)
from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend_preview import (
    build_preview as _build_preview_impl,
    session_sort_key,
)
from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend_processes import (
    classify_pane_status as _classify_pane_status_impl,
    find_meaningful_pane_process_label as _find_meaningful_pane_process_label_impl,
)
from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import (
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
    strip_ansi_codes,
)


def _find_meaningful_pane_process_label(pane_pid: str) -> str | None:
    return _find_meaningful_pane_process_label_impl(pane_pid)


def _classify_pane_status(pane: dict[str, str]) -> tuple[str, str]:
    return _classify_pane_status_impl(
        pane,
        pane_process_label_finder=_find_meaningful_pane_process_label,
    )


def _build_preview(session_name: str) -> str:
    return _build_preview_impl(
        session_name=session_name,
        run_command_fn=run_command,
        classify_pane_status_fn=_classify_pane_status,
    )


def choose_session(
    name: str | None,
    new_session: bool,
    kill_all: bool,
    window: bool = False,
) -> tuple[str, str | None]:
    if name is not None:
        if window:
            return ("run_script", attach_script_from_name(name=name, quote_fn=quote))
        return ("run_script", f"tmux attach -t {quote(name)}")
    if new_session:
        return ("run_script", new_session_script(kill_all=kill_all))

    result = run_command(["tmux", "list-sessions", "-F", "#S"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(
        key=lambda session_name: session_sort_key(
            session_name=session_name,
            natural_sort_key_fn=natural_sort_key,
            strip_ansi_codes_fn=strip_ansi_codes,
        )
    )

    if len(sessions) == 0:
        return ("run_script", "tmux new-session")
    if not window and len(sessions) == 1:
        return ("run_script", f"tmux attach -t {quote(sessions[0])}")

    if window:
        option_to_script, options_to_preview_mapping = build_window_target_options(
            sessions=sessions,
            run_command_fn=run_command,
            classify_pane_status_fn=_classify_pane_status,
            quote_fn=quote,
        )
        if len(option_to_script) == 0:
            return ("error", "No tmux windows or panes are available to attach to.")
        if len(option_to_script) == 1:
            return ("run_script", next(iter(option_to_script.values())))
        options_to_preview_mapping[NEW_SESSION_LABEL] = (
            "backend: tmux\naction: create a fresh session\n\ntmux new-session"
        )
        options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
            "backend: tmux\naction: kill the tmux server, then start a new session\n\ntmux kill-server\ntmux new-session"
        )
        selection = interactive_choose_with_preview(
            msg="Choose a tmux window or pane to attach to:",
            options_to_preview_mapping=options_to_preview_mapping,
        )
        if selection is None:
            return ("error", "No tmux window or pane selected.")
        if selection == NEW_SESSION_LABEL:
            return ("run_script", new_session_script(kill_all=kill_all))
        if selection == KILL_ALL_AND_NEW_LABEL:
            return ("run_script", "tmux kill-server\ntmux new-session")
        script = option_to_script.get(selection)
        if script is None:
            return ("error", f"Unknown tmux target selected: {selection}")
        return ("run_script", script)

    options_to_preview_mapping = {session_name: _build_preview(session_name) for session_name in sessions}
    options_to_preview_mapping[NEW_SESSION_LABEL] = "backend: tmux\naction: create a fresh session\n\ntmux new-session"
    options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
        "backend: tmux\naction: kill the tmux server, then start a new session\n\ntmux kill-server\ntmux new-session"
    )
    session_name = interactive_choose_with_preview(
        msg="Choose a tmux session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if session_name is None:
        return ("error", "No tmux session selected.")
    if session_name == NEW_SESSION_LABEL:
        return ("run_script", new_session_script(kill_all=kill_all))
    if session_name == KILL_ALL_AND_NEW_LABEL:
        return ("run_script", "tmux kill-server\ntmux new-session")
    return ("run_script", f"tmux attach -t {quote(session_name)}")
