from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options import (
    attach_script_from_name,
    build_idle_kill_script_for_sessions,
    build_kill_target_options,
    build_window_target_options,
    kill_script_for_target,
    new_session_script,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import (
    build_preview as _build_preview_impl,
    session_sort_key,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes import (
    classify_pane_status as _classify_pane_status_impl,
    find_meaningful_pane_process_label as _find_meaningful_pane_process_label_impl,
)
from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    AttachSessionChoice,
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    collect_selected_option_scripts,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
    strip_ansi_codes,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_impl import KilledTarget


def _strip_active_marker(label: str) -> str:
    if label.endswith(" *"):
        return label[:-2]
    return label


def _parent_tmux_window_label(*, selection_label: str, labels_by_normalized_label: dict[str, str]) -> str | None:
    normalized_label = _strip_active_marker(selection_label)
    prefix, separator, _process_label = normalized_label.rpartition(" ")
    if separator == "":
        return None
    window_label, pane_separator, pane_index = prefix.rpartition(".")
    if pane_separator == "" or not pane_index.isdecimal():
        return None
    return labels_by_normalized_label.get(window_label)


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


def list_session_names() -> list[str]:
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
    return sessions


def choose_existing_session_name(
    msg: str = "Choose a tmux session:",
) -> tuple[str, str]:
    sessions = list_session_names()
    if len(sessions) == 0:
        return ("error", "No tmux sessions are available.")

    session_name = interactive_choose_with_preview(
        msg=msg,
        options_to_preview_mapping={session_name: _build_preview(session_name) for session_name in sessions},
    )
    if session_name is None:
        return ("error", "No tmux session selected.")
    return ("session_name", session_name)


def choose_session(
    name: str | None,
    new_session: bool,
    kill_all: bool,
    window: bool = False,
) -> AttachSessionChoice:
    if name is not None:
        return ("handoff_script", attach_script_from_name(name=name, quote_fn=quote))
    if new_session:
        return ("handoff_script", new_session_script(kill_all=kill_all))

    sessions = list_session_names()

    if len(sessions) == 0:
        return ("handoff_script", new_session_script(kill_all=False))
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
            return ("handoff_script", next(iter(option_to_script.values())))
        options_to_preview_mapping[NEW_SESSION_LABEL] = (
            f"backend: tmux\naction: create a fresh session\n\n{new_session_script(kill_all=kill_all)}"
        )
        if not kill_all:
            options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
                f"backend: tmux\naction: kill the tmux server, then start a new session\n\n{new_session_script(kill_all=True)}"
            )
        selection = interactive_choose_with_preview(
            msg="Choose a tmux window or pane to attach to:",
            options_to_preview_mapping=options_to_preview_mapping,
        )
        if selection is None:
            return ("error", "No tmux target selected.")
        if selection == NEW_SESSION_LABEL:
            return ("handoff_script", new_session_script(kill_all=kill_all))
        if selection == KILL_ALL_AND_NEW_LABEL:
            return ("handoff_script", new_session_script(kill_all=True))
        script = option_to_script.get(selection)
        if script is None:
            return ("error", f"Unknown tmux target selected: {selection}")
        return ("handoff_script", script)

    options_to_preview_mapping = {session_name: _build_preview(session_name) for session_name in sessions}
    options_to_preview_mapping[NEW_SESSION_LABEL] = (
        f"backend: tmux\naction: create a fresh session\n\n{new_session_script(kill_all=kill_all)}"
    )
    if not kill_all:
        options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
            f"backend: tmux\naction: kill the tmux server, then start a new session\n\n{new_session_script(kill_all=True)}"
        )
    session_name = interactive_choose_with_preview(
        msg="Choose a tmux session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if session_name is None:
        return ("error", "No tmux session selected.")
    if session_name == NEW_SESSION_LABEL:
        return ("handoff_script", new_session_script(kill_all=kill_all))
    if session_name == KILL_ALL_AND_NEW_LABEL:
        return ("handoff_script", new_session_script(kill_all=True))
    return ("handoff_script", attach_script_from_name(name=session_name, quote_fn=quote))


def _choose_idle_kill_target(sessions: list[str]) -> tuple[str, str | None, list[KilledTarget]]:
    if len(sessions) == 0:
        return ("error", "No tmux sessions are available to inspect for idle panes or windows.", [])
    try:
        script, killed_targets = build_idle_kill_script_for_sessions(
            sessions=sessions,
            run_command_fn=run_command,
            classify_pane_status_fn=_classify_pane_status,
            quote_fn=quote,
        )
    except ValueError as error:
        return ("error", str(error), [])
    if script.strip():
        return ("run_script", script, killed_targets)
    if len(sessions) == 1:
        return ("error", f"No idle-shell tmux panes or windows are available to kill in session '{sessions[0]}'.", [])
    return ("error", "No idle-shell tmux panes or windows are available to kill.", [])


def choose_kill_target(
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    if idle:
        if window:
            return ("error", "--idle cannot be used together with --window.", [])
        if kill_all:
            return _choose_idle_kill_target(sessions=list_session_names())
        if name is not None:
            return _choose_idle_kill_target(sessions=[name])
        action, payload = choose_existing_session_name(
            msg="Choose a tmux session to clean idle panes/windows:",
        )
        if action != "session_name":
            return ("error", payload, [])
        return _choose_idle_kill_target(sessions=[payload])

    if kill_all:
        return ("run_script", "tmux kill-server", [])
    if name is not None:
        return ("run_script", kill_script_for_target(session_name=name, quote_fn=quote), [])

    sessions = list_session_names()

    if len(sessions) == 0:
        return ("error", "No tmux sessions are available to kill.", [])

    options_to_script: dict[str, str] = {}
    options_to_preview_mapping: dict[str, str] = {}
    option_parent_labels: dict[str, tuple[str, ...]] = {}

    if window:
        for session_name in sessions:
            session_label = f"[{session_name}] SESSION"
            options_to_script[session_label] = kill_script_for_target(
                session_name=session_name,
                quote_fn=quote,
            )
            options_to_preview_mapping[session_label] = _build_preview(session_name)
            option_parent_labels[session_label] = ()
            window_scripts, window_previews = build_kill_target_options(
                sessions=[session_name],
                run_command_fn=run_command,
                classify_pane_status_fn=_classify_pane_status,
                quote_fn=quote,
            )
            options_to_script.update(window_scripts)
            options_to_preview_mapping.update(window_previews)
            labels_by_normalized_label = {
                _strip_active_marker(target_label): target_label
                for target_label in window_scripts
            }
            for target_label in window_scripts:
                parent_labels = [session_label]
                window_parent_label = _parent_tmux_window_label(
                    selection_label=target_label,
                    labels_by_normalized_label=labels_by_normalized_label,
                )
                if window_parent_label is not None:
                    parent_labels.append(window_parent_label)
                option_parent_labels[target_label] = tuple(parent_labels)
        msg = "Choose a tmux session, window, or pane to kill:"
    else:
        for session_name in sessions:
            options_to_script[session_name] = kill_script_for_target(
                session_name=session_name,
                quote_fn=quote,
            )
            options_to_preview_mapping[session_name] = _build_preview(session_name)
            option_parent_labels[session_name] = ()
        msg = "Choose a tmux session to kill:"

    selections = interactive_choose_with_preview(
        msg=msg,
        options_to_preview_mapping=options_to_preview_mapping,
        multi=True,
    )
    if len(selections) == 0:
        return ("error", "No tmux target selected.", [])
    scripts, unknown_selection = collect_selected_option_scripts(
        selections=selections,
        options_to_script=options_to_script,
        option_parent_labels=option_parent_labels,
    )
    if unknown_selection is not None:
        return ("error", f"Unknown tmux target selected: {unknown_selection}", [])
    return ("run_script", "\n".join(scripts), [])
