import re
from typing import Literal

from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    TraceBackend,
    TraceTarget,
)


type TraceSessionChoice = tuple[Literal["error"], str] | tuple[Literal["session_names"], list[str]]


def _parse_session_selectors(session_selectors: str) -> list[str]:
    selectors = [selector.strip() for selector in session_selectors.split(",")]
    if len(selectors) == 0 or any(selector == "" for selector in selectors):
        raise ValueError("SESSION_NAMES must contain non-empty comma-separated selectors.")
    return selectors


def _matches_session_pattern(session_name: str, pattern: str) -> bool:
    regex_parts: list[str] = []
    for character in pattern:
        match character:
            case "*":
                regex_parts.append(".*")
            case "?":
                regex_parts.append(".")
            case _:
                regex_parts.append(re.escape(character))
    return re.fullmatch("".join(regex_parts), session_name) is not None


def _load_trace_targets(backend: TraceBackend) -> list[TraceTarget]:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names

            return [TraceTarget(label=session_name, session_name=session_name, match_names=(session_name,)) for session_name in list_session_names()]
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_herdr import list_trace_targets

            targets, error = list_trace_targets()
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_aoe import list_trace_targets

            targets, error = list_trace_targets()
    if targets is None:
        raise ValueError(error or f"Unable to list {backend} sessions.")
    return targets


def resolve_trace_session_names(backend: TraceBackend, session_selectors: str) -> list[str]:
    selectors = _parse_session_selectors(session_selectors=session_selectors)
    if not any("*" in selector or "?" in selector for selector in selectors):
        return list(dict.fromkeys(selectors))

    targets = _load_trace_targets(backend=backend)
    available_names = list(dict.fromkeys(match_name for target in targets for match_name in target.match_names))
    resolved_session_names: list[str] = []
    for selector in selectors:
        if "*" not in selector and "?" not in selector:
            resolved_session_names.append(selector)
            continue
        matched_targets = [
            target
            for target in targets
            if any(_matches_session_pattern(session_name=match_name, pattern=selector) for match_name in target.match_names)
        ]
        if len(matched_targets) == 0:
            raise ValueError(f"Session selector '{selector}' matched no {backend} sessions. Available names: {available_names}")
        resolved_session_names.extend(target.session_name for target in matched_targets)
    return list(dict.fromkeys(resolved_session_names))


def choose_trace_session_names(backend: TraceBackend) -> TraceSessionChoice:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_existing_session_names

            return choose_existing_session_names(msg="Choose tmux sessions to trace:")
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_herdr import choose_existing_workspace_names

            return choose_existing_workspace_names(msg="Choose Herdr workspaces to trace:")
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_aoe import choose_existing_session_names

            return choose_existing_session_names(msg="Choose AoE sessions to trace:")
