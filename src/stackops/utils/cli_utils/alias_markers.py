import re
from collections.abc import Callable

import typer
from typer.models import CommandInfo, TyperInfo


ALIAS_MARKER_PATTERN = re.compile(r"<[^>\s]+>")


def apply_alias_markers(app: typer.Typer) -> typer.Typer:
    _apply_command_alias_markers(app.registered_commands)
    _apply_group_alias_markers(app.registered_groups)
    for group in app.registered_groups:
        if group.typer_instance is not None:
            apply_alias_markers(group.typer_instance)
    return app


def _apply_command_alias_markers(commands: list[CommandInfo]) -> None:
    aliases_by_callback: dict[Callable[..., object], list[str]] = {}
    for command in commands:
        if command.hidden and command.name is not None and len(command.name) == 1 and command.callback is not None:
            aliases_by_callback.setdefault(command.callback, []).append(command.name)

    for command in commands:
        if command.hidden or command.callback is None:
            continue
        aliases = aliases_by_callback.get(command.callback)
        if aliases is None:
            continue
        alias_marker = _alias_marker(aliases)
        help_text = _with_alias_marker(help_text=command.help, alias_marker=alias_marker)
        short_help = _with_alias_marker(help_text=command.short_help, alias_marker=alias_marker)
        if help_text is not None:
            command.help = help_text
        if short_help is not None:
            command.short_help = short_help


def _apply_group_alias_markers(groups: list[TyperInfo]) -> None:
    visible_group: TyperInfo | None = None
    for group in groups:
        if group.hidden is not True:
            visible_group = group
            continue
        if visible_group is None or group.name is None or len(group.name) != 1:
            continue
        alias = group.name
        alias_marker = _alias_marker([alias])
        help_text = _with_alias_marker(help_text=visible_group.help, alias_marker=alias_marker)
        short_help = _with_alias_marker(help_text=visible_group.short_help, alias_marker=alias_marker)
        if help_text is not None:
            visible_group.help = help_text
        if short_help is not None:
            visible_group.short_help = short_help


def _alias_marker(aliases: list[str]) -> str:
    ordered_aliases = sorted(set(aliases))
    return ", ".join(f"<{alias}>" for alias in ordered_aliases)


def _with_alias_marker(help_text: object, alias_marker: str) -> str | None:
    if not isinstance(help_text, str):
        return None
    if ALIAS_MARKER_PATTERN.search(help_text):
        return help_text
    return f"{alias_marker} {help_text}"
