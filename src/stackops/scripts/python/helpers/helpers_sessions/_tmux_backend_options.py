from subprocess import CompletedProcess
from typing import Callable

from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_helpers import build_tmux_attach_or_switch_command
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import (
    build_pane_preview,
    build_window_preview,
    collect_session_snapshot,
)


def new_session_script(kill_all: bool) -> str:
    command = "tmux new-session"
    if kill_all:
        command = f"tmux kill-server\n{command}"
    return command


def attach_script_for_target(
    session_name: str,
    quote_fn: Callable[[str], str],
    window_target: str | None = None,
    pane_index: str | None = None,
) -> str:
    commands: list[str] = []
    if window_target:
        target = f"{session_name}:{window_target}"
        commands.append(f"tmux select-window -t {quote_fn(target)}")
        if pane_index:
            commands.append(f"tmux select-pane -t {quote_fn(f'{target}.{pane_index}')}")
    commands.append(build_tmux_attach_or_switch_command(session_name=session_name))
    return "\n".join(commands)


def kill_script_for_target(
    session_name: str,
    quote_fn: Callable[[str], str],
    window_target: str | None = None,
    pane_index: str | None = None,
) -> str:
    if window_target is None:
        return f"tmux kill-session -t {quote_fn(session_name)}"

    target = f"{session_name}:{window_target}"
    if pane_index:
        return f"tmux kill-pane -t {quote_fn(f'{target}.{pane_index}')}"
    return f"tmux kill-window -t {quote_fn(target)}"


def attach_script_from_name(name: str, quote_fn: Callable[[str], str]) -> str:
    session_name, separator, target = name.partition(":")
    if not separator or not session_name or not target:
        return build_tmux_attach_or_switch_command(session_name=name)
    window_target, pane_separator, pane_index = target.rpartition(".")
    if pane_separator:
        return attach_script_for_target(
            session_name=session_name,
            quote_fn=quote_fn,
            window_target=window_target,
            pane_index=pane_index,
        )
    return attach_script_for_target(session_name=session_name, quote_fn=quote_fn, window_target=target)


def _build_target_options(
    sessions: list[str],
    run_command_fn: Callable[[list[str]], CompletedProcess[str]],
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
    quote_fn: Callable[[str], str],
    script_builder_fn: Callable[[str, Callable[[str], str], str | None, str | None], str],
) -> tuple[dict[str, str], dict[str, str]]:
    options_to_scripts: dict[str, str] = {}
    options_to_previews: dict[str, str] = {}
    for session_name in sessions:
        windows, panes_by_window, pane_warning = collect_session_snapshot(
            session_name=session_name,
            run_command_fn=run_command_fn,
        )
        if windows is None:
            continue
        for window in windows:
            window_label = f"[{session_name}] {window['window_index']}:{window['window_name']}"
            if window["window_active"]:
                window_label += " *"
            window_panes = panes_by_window.get(window["window_index"], [])
            options_to_scripts[window_label] = script_builder_fn(session_name, quote_fn, window["window_index"], None)
            options_to_previews[window_label] = build_window_preview(
                session_name=session_name,
                window=window,
                panes=window_panes,
                pane_warning=pane_warning,
                classify_pane_status_fn=classify_pane_status_fn,
            )
            for pane in window_panes:
                process_name, _ = classify_pane_status_fn(pane)
                pane_label = f"[{session_name}] {window['window_index']}:{window['window_name']}.{pane['pane_index']} {process_name}"
                if pane["pane_active"]:
                    pane_label += " *"
                options_to_scripts[pane_label] = script_builder_fn(session_name, quote_fn, window["window_index"], pane["pane_index"])
                options_to_previews[pane_label] = build_pane_preview(
                    session_name=session_name,
                    window=window,
                    pane=pane,
                    classify_pane_status_fn=classify_pane_status_fn,
                )
    return (options_to_scripts, options_to_previews)


def build_window_target_options(
    sessions: list[str],
    run_command_fn: Callable[[list[str]], CompletedProcess[str]],
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
    quote_fn: Callable[[str], str],
) -> tuple[dict[str, str], dict[str, str]]:
    return _build_target_options(
        sessions=sessions,
        run_command_fn=run_command_fn,
        classify_pane_status_fn=classify_pane_status_fn,
        quote_fn=quote_fn,
        script_builder_fn=attach_script_for_target,
    )


def build_kill_target_options(
    sessions: list[str],
    run_command_fn: Callable[[list[str]], CompletedProcess[str]],
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
    quote_fn: Callable[[str], str],
) -> tuple[dict[str, str], dict[str, str]]:
    return _build_target_options(
        sessions=sessions,
        run_command_fn=run_command_fn,
        classify_pane_status_fn=classify_pane_status_fn,
        quote_fn=quote_fn,
        script_builder_fn=kill_script_for_target,
    )
