from typing import Literal

from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget
from stackops.scripts.python.helpers.helpers_sessions.session_trace_selection import (
    matches_session_pattern,
)


type KillBackend = Literal["tmux", "herdr", "aoe"]


def _choose_exact_kill_target(
    backend: KillBackend,
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
    delete: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    match backend:
        case "tmux":
            if delete:
                return ("error", "--delete is only supported by the Herdr backend.", [])
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_kill_target as _tmux

            return _tmux(name=name, kill_all=kill_all, idle=idle, window=window)
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import choose_kill_target as _herdr

            return _herdr(name=name, kill_all=kill_all, idle=idle, window=window, delete=delete)
        case "aoe":
            if delete:
                return ("error", "--delete is only supported by the Herdr backend.", [])
            from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import choose_kill_target as _aoe

            return _aoe(name=name, kill_all=kill_all, idle=idle, window=window)
    raise ValueError(f"Unsupported backend: {backend}")


def _list_killable_session_names(backend: KillBackend, delete: bool) -> list[str] | None:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names

            return list_session_names()
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import list_killable_session_names

            return list_killable_session_names(delete=delete)
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import list_killable_session_names

            return list_killable_session_names()
    raise ValueError(f"Unsupported backend: {backend}")


def choose_kill_target(
    backend: KillBackend,
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
    delete: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    if name is None or not any(character in name for character in ("*", "?")):
        return _choose_exact_kill_target(
            backend=backend,
            name=name,
            kill_all=kill_all,
            idle=idle,
            window=window,
            delete=delete,
        )

    available_names = _list_killable_session_names(backend=backend, delete=delete)
    if available_names is None:
        return ("error", f"Unable to list {backend} sessions.", [])
    matched_names = [
        session_name
        for session_name in available_names
        if matches_session_pattern(session_name=session_name, pattern=name)
    ]
    if len(matched_names) == 0:
        return (
            "error",
            f"Session selector '{name}' matched no killable {backend} sessions. Available names: {available_names}",
            [],
        )

    scripts: list[str] = []
    killed_targets: list[KilledTarget] = []
    for matched_name in matched_names:
        action, payload, matched_killed_targets = _choose_exact_kill_target(
            backend=backend,
            name=matched_name,
            kill_all=False,
            idle=idle,
            window=False,
            delete=delete,
        )
        if action == "error":
            return (action, payload, matched_killed_targets)
        if action != "run_script" or payload is None:
            return ("error", f"Kill selector '{name}' did not produce an executable script.", [])
        scripts.append(payload)
        killed_targets.extend(matched_killed_targets)
    return ("run_script", "\n".join(scripts), killed_targets)
