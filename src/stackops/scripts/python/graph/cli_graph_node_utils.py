from typing import Any, Sequence

from stackops.scripts.python.graph.cli_graph_shared import Registration


def choose_short_name(name: str, aliases: list[dict[str, Any]]) -> str:
    candidates: list[str] = [name]
    for alias in aliases:
        alias_name = alias.get("name")
        if isinstance(alias_name, str) and alias_name:
            candidates.append(alias_name)

    non_empty_candidates = [candidate for candidate in candidates if candidate]
    if not non_empty_candidates:
        return ""
    return min(non_empty_candidates, key=len)


def extend_path_tokens(parent_tokens: tuple[str, ...], name: str) -> tuple[str, ...]:
    if not name:
        return parent_tokens
    return (*parent_tokens, name)


def join_command_path(tokens: Sequence[str]) -> str:
    return " ".join(token for token in tokens if token)


def choose_primary(registrations: list[Registration]) -> Registration:
    visible = [reg for reg in registrations if not reg.hidden]
    return visible[0] if visible else registrations[0]


def build_aliases(
    registrations: list[Registration], primary: Registration
) -> list[dict[str, Any]]:
    aliases: list[dict[str, Any]] = []
    for reg in registrations:
        if reg is primary:
            continue
        entry: dict[str, Any] = {"name": reg.name or ""}
        if reg.hidden:
            entry["hidden"] = True
        if isinstance(reg.help, str) and reg.help:
            entry["help"] = reg.help
        if isinstance(reg.short_help, str) and reg.short_help:
            entry["short_help"] = reg.short_help
        aliases.append(entry)
    return aliases


def select_help(reg: Registration, default: str | None) -> str:
    if isinstance(reg.help, str) and reg.help:
        return reg.help
    if default:
        return default
    return reg.name or ""