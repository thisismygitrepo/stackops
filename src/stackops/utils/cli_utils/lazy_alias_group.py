from collections.abc import MutableMapping

import typer
import typer.main
from typer import _click
from typer.core import TyperGroup
from typer.models import DefaultPlaceholder, TyperInfo


class LazyAliasGroup(TyperGroup):
    source_app: typer.Typer

    @property
    def commands(self) -> MutableMapping[str, _click.Command]:
        if self._converted_commands is None:
            self._converted_commands = typer.main.get_group(self.source_app).commands
        return self._converted_commands

    @commands.setter
    def commands(self, value: MutableMapping[str, _click.Command]) -> None:
        self._converted_commands: MutableMapping[str, _click.Command] | None = None


def _lazy_alias_group_class(source_app: typer.Typer) -> type[LazyAliasGroup]:
    class SourceBoundLazyAliasGroup(LazyAliasGroup):
        pass

    SourceBoundLazyAliasGroup.source_app = source_app
    return SourceBoundLazyAliasGroup


def _shape(app: typer.Typer) -> tuple[tuple[str | None, bool | None], ...]:
    commands = tuple((command.name or getattr(command.callback, "__name__", None), command.hidden) for command in app.registered_commands)
    groups = tuple((group.name, group.hidden) for group in app.registered_groups)
    return commands + groups


def _has_callback(app: typer.Typer) -> bool:
    configured_callback = app.info.callback
    if isinstance(configured_callback, DefaultPlaceholder):
        configured_callback = configured_callback.value
    return app.registered_callback is not None or configured_callback is not None


def _is_deferrable_duplicate(alias_app: typer.Typer, source_app: typer.Typer) -> bool:
    if alias_app is source_app:
        return False
    if _has_callback(alias_app) or _has_callback(source_app):
        return False
    if len(source_app.registered_groups) == 0 and len(source_app.registered_commands) < 2:
        return False
    return _shape(alias_app) == _shape(source_app)


def defer_alias_group_conversion(groups: list[TyperInfo]) -> None:
    visible_group: TyperInfo | None = None
    for group in groups:
        if group.hidden is not True:
            visible_group = group
            continue
        if visible_group is None or group.name is None or len(group.name) != 1:
            continue
        alias_app = group.typer_instance
        source_app = visible_group.typer_instance
        if alias_app is None or source_app is None or not _is_deferrable_duplicate(alias_app=alias_app, source_app=source_app):
            continue
        alias_app.registered_commands.clear()
        alias_app.registered_groups.clear()
        alias_app.info.cls = _lazy_alias_group_class(source_app=source_app)
