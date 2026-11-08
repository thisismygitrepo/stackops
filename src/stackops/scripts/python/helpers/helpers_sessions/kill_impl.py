from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget
from stackops.scripts.python.helpers.helpers_sessions.session_trace_selection import (
    matches_session_pattern,
    parse_session_selectors,
)
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer


def _choose_exact_kill_target(
    backend: SessionMultiplexer,
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
    delete: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    match backend:
        case "tmux":
            if delete:
                return ("error", "--delete is only supported by the Herdr and Zellij backends.", [])
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_kill_target as _tmux

            return _tmux(name=name, kill_all=kill_all, idle=idle, window=window)
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import choose_kill_target as _herdr

            return _herdr(name=name, kill_all=kill_all, idle=idle, window=window, delete=delete)
        case "tuios":
            if delete:
                return ("error", "--delete is only supported by the Herdr and Zellij backends.", [])
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_kill import choose_kill_target as _tuios

            return _tuios(name=name, kill_all=kill_all, idle=idle, window=window)
        case "zellij":
            from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_kill import choose_kill_target as _zellij

            return _zellij(name=name, kill_all=kill_all, idle=idle, window=window, delete=delete)
        case "aoe":
            if delete:
                return ("error", "--delete is only supported by the Herdr and Zellij backends.", [])
            from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import choose_kill_target as _aoe

            return _aoe(name=name, kill_all=kill_all, idle=idle, window=window)
    raise ValueError(f"Unsupported backend: {backend}")


def _list_killable_session_names(backend: SessionMultiplexer, delete: bool) -> list[str] | None:
    match backend:
        case "zellij":
            from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_session_entries

            return [session.name for session in list_session_entries() if session.exited == delete]
        case "tuios":
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend import list_session_names

            return list_session_names()
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names

            return list_session_names()
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import list_killable_session_names as list_herdr_killable_session_names

            return list_herdr_killable_session_names(delete=delete)
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import list_killable_session_names as list_aoe_killable_session_names

            return list_aoe_killable_session_names()
    raise ValueError(f"Unsupported backend: {backend}")


def choose_kill_target(
    backend: SessionMultiplexer,
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
    delete: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    if name is None:
        return _choose_exact_kill_target(
            backend=backend,
            name=None,
            kill_all=kill_all,
            idle=idle,
            window=window,
            delete=delete,
        )
    try:
        selectors = parse_session_selectors(session_selectors=name)
    except ValueError as error:
        return ("error", str(error), [])
    glob_selectors = {selector for selector in selectors if "*" in selector or "?" in selector}
    if len(selectors) == 1 and len(glob_selectors) == 0:
        return _choose_exact_kill_target(
            backend=backend,
            name=selectors[0],
            kill_all=kill_all,
            idle=idle,
            window=window,
            delete=delete,
        )

    available_names: list[str] = []
    if len(glob_selectors) > 0:
        try:
            listed_names = _list_killable_session_names(backend=backend, delete=delete)
        except ValueError as error:
            return ("error", str(error), [])
        if listed_names is None:
            return ("error", f"Unable to list {backend} sessions.", [])
        available_names = listed_names
    resolved_names: list[str] = []
    for selector in selectors:
        if selector not in glob_selectors:
            resolved_names.append(selector)
            continue
        selector_matches = [
            session_name
            for session_name in available_names
            if matches_session_pattern(session_name=session_name, pattern=selector)
        ]
        if len(selector_matches) == 0:
            return (
                "error",
                f"Session selector '{selector}' matched no killable {backend} sessions. Available names: {available_names}",
                [],
            )
        resolved_names.extend(selector_matches)
    matched_names = list(dict.fromkeys(resolved_names))
    if backend == "zellij":
        import os

        matched_names.sort(key=lambda session_name: session_name == os.environ.get("ZELLIJ_SESSION_NAME"))

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
