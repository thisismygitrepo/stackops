from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend_layout import summarize_layout
from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend_metadata import (
    build_metadata_summary,
    find_latest_session_file,
    get_live_tab_names as _get_live_tab_names_impl,
    read_session_metadata as _read_session_metadata_impl,
)
from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend_options import (
    build_kill_target_options,
    build_window_target_options,
    kill_script_for_target,
    new_session_script,
)
from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend_preview import (
    build_preview as _build_preview_impl,
    session_is_current as _session_is_current_impl,
    session_is_exited as _session_is_exited_impl,
    session_name as _session_name_impl,
    session_sort_key as _session_sort_key_impl,
)
from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import (
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    STANDARD,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
    strip_ansi_codes,
)


def _session_sort_key(raw_line: str) -> tuple[bool, list[int | str]]:
    return _session_sort_key_impl(
        raw_line=raw_line,
        natural_sort_key_fn=natural_sort_key,
        strip_ansi_codes_fn=strip_ansi_codes,
    )


def _session_name(raw_line: str) -> str:
    return _session_name_impl(raw_line=raw_line, strip_ansi_codes_fn=strip_ansi_codes)


def _session_is_exited(raw_line: str) -> bool:
    return _session_is_exited_impl(raw_line=raw_line, strip_ansi_codes_fn=strip_ansi_codes)


def _session_is_current(raw_line: str) -> bool:
    return _session_is_current_impl(raw_line=raw_line, strip_ansi_codes_fn=strip_ansi_codes)


def _read_session_metadata(session_name: str) -> tuple[list[dict[str, object]], list[dict[str, object]]] | None:
    return _read_session_metadata_impl(session_name)


def _get_live_tab_names(session_name: str) -> list[str]:
    return _get_live_tab_names_impl(session_name=session_name, run_command_fn=run_command)


def _build_preview(raw_line: str) -> str:
    return _build_preview_impl(
        raw_line=raw_line,
        run_command_fn=run_command,
        strip_ansi_codes_fn=strip_ansi_codes,
        summarize_layout_fn=summarize_layout,
        find_latest_session_file_fn=find_latest_session_file,
        read_session_metadata_fn=_read_session_metadata,
        build_metadata_summary_fn=build_metadata_summary,
        get_live_tab_names_fn=_get_live_tab_names,
    )


def choose_session(
    name: str | None,
    new_session: bool,
    kill_all: bool,
    window: bool = False,
) -> tuple[str, str | None]:
    if name is not None:
        return ("run_script", f"zellij attach {quote(name)}")
    if new_session:
        return ("run_script", new_session_script(standard_layout=STANDARD, quote_fn=quote, kill_all=kill_all))

    result = run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(key=_session_sort_key)

    if any(_session_is_current(session) for session in sessions):
        return ("error", "Already in a Zellij session, avoiding nesting and exiting.")
    if len(sessions) == 0:
        return ("run_script", f"zellij --layout {quote(STANDARD)}")

    if window:
        active_sessions = [_session_name(session) for session in sessions if not _session_is_exited(session)]
        if not active_sessions:
            return ("error", "No active Zellij sessions are available for --window selection.")
        option_to_script, options_to_preview_mapping = build_window_target_options(
            active_sessions=active_sessions,
            read_session_metadata_fn=_read_session_metadata,
            get_live_tab_names_fn=_get_live_tab_names,
            quote_fn=quote,
        )
        if len(option_to_script) == 0:
            return ("error", "No Zellij tabs or panes are available to attach to.")
        if len(option_to_script) == 1:
            return ("run_script", next(iter(option_to_script.values())))
        options_to_preview_mapping[NEW_SESSION_LABEL] = (
            f"backend: zellij\naction: create a fresh session\n\nzellij --layout {STANDARD}"
        )
        options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
            f"backend: zellij\naction: kill every existing session, then start a new one\n\nzellij kill-all-sessions --yes\nzellij --layout {STANDARD}"
        )
        selection = interactive_choose_with_preview(
            msg="Choose a Zellij tab or pane to attach to:",
            options_to_preview_mapping=options_to_preview_mapping,
        )
        if selection is None:
            return ("error", "No Zellij tab or pane selected.")
        if selection == NEW_SESSION_LABEL:
            return ("run_script", new_session_script(standard_layout=STANDARD, quote_fn=quote, kill_all=kill_all))
        if selection == KILL_ALL_AND_NEW_LABEL:
            return ("run_script", f"zellij kill-all-sessions --yes\nzellij --layout {quote(STANDARD)}")
        script = option_to_script.get(selection)
        if script is None:
            return ("error", f"Unknown Zellij target selected: {selection}")
        return ("run_script", script)

    if len(sessions) == 1:
        session_name = _session_name(sessions[0])
        return ("run_script", f"zellij attach {quote(session_name)}")

    display_to_raw_session = {strip_ansi_codes(session): session for session in sessions}
    display_to_session = {
        display: _session_name(raw_session)
        for display, raw_session in display_to_raw_session.items()
    }
    options_to_preview_mapping = {
        display: _build_preview(raw_session)
        for display, raw_session in display_to_raw_session.items()
    }
    options_to_preview_mapping[NEW_SESSION_LABEL] = (
        f"backend: zellij\naction: create a fresh session\n\nzellij --layout {STANDARD}"
    )
    options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
        f"backend: zellij\naction: kill every existing session, then start a new one\n\nzellij kill-all-sessions --yes\nzellij --layout {STANDARD}"
    )
    session_label = interactive_choose_with_preview(
        msg="Choose a Zellij session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if session_label is None:
        return ("error", "No Zellij session selected.")
    if session_label == NEW_SESSION_LABEL:
        return ("run_script", new_session_script(standard_layout=STANDARD, quote_fn=quote, kill_all=kill_all))
    if session_label == KILL_ALL_AND_NEW_LABEL:
        return ("run_script", f"zellij kill-all-sessions --yes\nzellij --layout {quote(STANDARD)}")
    selected_session_name: str | None = display_to_session.get(session_label)
    if selected_session_name is None:
        return ("error", f"Unknown Zellij session selected: {session_label}")
    return ("run_script", f"zellij attach {quote(selected_session_name)}")


def get_session_tabs() -> list[tuple[str, str]]:
    result = run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [strip_ansi_codes(session) for session in sessions]
    active_sessions = [session for session in sessions if "EXITED" not in session]
    tabs: list[tuple[str, str]] = []
    for session_line in active_sessions:
        session_name = _session_name(session_line)
        tab_names = _get_live_tab_names(session_name)
        for tab in tab_names:
            tabs.append((session_name, tab))
    return tabs


def choose_kill_target(
    name: str | None,
    kill_all: bool = False,
    window: bool = False,
) -> tuple[str, str | None]:
    if kill_all:
        return ("run_script", "zellij kill-all-sessions --yes")
    if name is not None:
        return ("run_script", kill_script_for_target(session_name=name, quote_fn=quote))

    result = run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(key=_session_sort_key)

    if len(sessions) == 0:
        return ("error", "No Zellij sessions are available to kill.")

    if window:
        options_to_script: dict[str, str] = {}
        options_to_preview_mapping: dict[str, str] = {}
        for raw_session in sessions:
            session_name = _session_name(raw_session)
            session_label = f"[{session_name}] SESSION"
            if _session_is_current(raw_session):
                session_label += " (current)"
            elif _session_is_exited(raw_session):
                session_label += " (exited)"
            options_to_script[session_label] = kill_script_for_target(
                session_name=session_name,
                quote_fn=quote,
            )
            options_to_preview_mapping[session_label] = _build_preview(raw_session)
            if _session_is_exited(raw_session):
                continue
            kill_scripts, kill_previews = build_kill_target_options(
                active_sessions=[session_name],
                read_session_metadata_fn=_read_session_metadata,
                get_live_tab_names_fn=_get_live_tab_names,
                quote_fn=quote,
            )
            options_to_script.update(kill_scripts)
            options_to_preview_mapping.update(kill_previews)
        selections = interactive_choose_with_preview(
            msg="Choose a Zellij session, tab, or pane to kill:",
            options_to_preview_mapping=options_to_preview_mapping,
            multi=True,
        )
        if len(selections) == 0:
            return ("error", "No Zellij target selected.")
        scripts: list[str] = []
        seen: set[str] = set()
        for selection in selections:
            if selection in seen:
                continue
            seen.add(selection)
            script = options_to_script.get(selection)
            if script is None:
                return ("error", f"Unknown Zellij target selected: {selection}")
            scripts.append(script)
        return ("run_script", "\n".join(scripts))

    display_to_raw_session = {strip_ansi_codes(session): session for session in sessions}
    options_to_script = {
        display: kill_script_for_target(
            session_name=_session_name(raw_session),
            quote_fn=quote,
        )
        for display, raw_session in display_to_raw_session.items()
    }
    options_to_preview_mapping = {
        display: _build_preview(raw_session)
        for display, raw_session in display_to_raw_session.items()
    }
    session_labels = interactive_choose_with_preview(
        msg="Choose a Zellij session to kill:",
        options_to_preview_mapping=options_to_preview_mapping,
        multi=True,
    )
    if len(session_labels) == 0:
        return ("error", "No Zellij session selected.")
    session_scripts: list[str] = []
    seen_session_labels: set[str] = set()
    for session_label in session_labels:
        if session_label in seen_session_labels:
            continue
        seen_session_labels.add(session_label)
        script = options_to_script.get(session_label)
        if script is None:
            return ("error", f"Unknown Zellij session selected: {session_label}")
        session_scripts.append(script)
    return ("run_script", "\n".join(session_scripts))
