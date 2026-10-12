from collections.abc import Callable
from importlib import import_module
import inspect
import re
import subprocess
import sys
from typing import NotRequired, TypedDict, cast
import unicodedata

import pytest
import typer
from typer.core import TyperGroup, TyperOption
from typer.main import get_command

from stackops.scripts.python.graph.cli_graph_tree import build_cli_graph
from stackops.scripts.python.graph.cli_graph_shared import REPO_ROOT


class AppSource(TypedDict):
    app_factory: NotRequired[str]
    dispatches_to: NotRequired[str]


class AppNode(TypedDict):
    source: AppSource
    children: NotRequired[list["AppNode"]]


class CliGraph(TypedDict):
    root: AppNode


HELP_MARKER_PATTERN = re.compile(r"^(?P<emoji>\S) <(?P<alias>[A-Za-z])> \S")


def _registered_apps() -> list[tuple[str, typer.Typer]]:
    graph = cast(CliGraph, build_cli_graph())
    pending_nodes = [graph["root"]]
    factories: set[str] = set()
    while pending_nodes:
        node = pending_nodes.pop()
        pending_nodes.extend(node.get("children", []))
        source = node["source"]
        factory = source.get("app_factory", source.get("dispatches_to"))
        if factory is not None:
            factories.add(factory)

    apps: list[tuple[str, typer.Typer]] = []
    for factory_path in sorted(factories):
        module_name, _, factory_name = factory_path.rpartition(".")
        factory = cast(Callable[[], typer.Typer], getattr(import_module(module_name), factory_name))
        apps.append((factory_path, factory()))
    return apps


def test_visible_commands_lead_help_with_wide_emoji_and_hidden_alias_marker() -> None:
    violations: list[str] = []
    for factory_path, app in _registered_apps():
        pending_groups = [(factory_path, get_command(app))]
        while pending_groups:
            group_path, group = pending_groups.pop()
            if not isinstance(group, TyperGroup):
                continue
            for name, command in group.commands.items():
                if command.hidden:
                    continue
                location = f"""{group_path} {name}"""
                pending_groups.append((location, command))
                help_line = (command.short_help or command.help or "").strip().partition("\n")[0]
                match = HELP_MARKER_PATTERN.match(help_line)
                if match is None:
                    violations.append(f"""{location} help is not "<emoji> <letter> <text>": {help_line!r}""")
                    continue
                emoji, alias_name = match["emoji"], match["alias"]
                if unicodedata.east_asian_width(emoji) != "W":
                    violations.append(f"""{location} leads with narrow symbol {emoji!r}""")
                alias = group.commands.get(alias_name)
                if isinstance(command, TyperGroup):
                    is_alias = isinstance(alias, TyperGroup) and alias.hidden and alias.commands.keys() == command.commands.keys()
                else:
                    is_alias = (
                        alias is not None and alias.hidden and alias.callback is not None and command.callback is not None
                        and inspect.unwrap(alias.callback) is inspect.unwrap(command.callback)
                    )
                if not is_alias:
                    violations.append(f"""{location} marker <{alias_name}> is not a hidden alias of it""")
    assert violations == []


def test_registered_options_have_single_flags_and_distinct_letter_shortcuts() -> None:
    violations: list[str] = []
    for factory_path, app in _registered_apps():
        pending_commands = [(factory_path, get_command(app))]
        while pending_commands:
            command_path, command = pending_commands.pop()
            used_shorts: set[str] = {"-h"}
            for parameter in command.params:
                if not isinstance(parameter, TyperOption):
                    continue
                location = f"""{command_path}: {parameter.name}"""
                if parameter.secondary_opts:
                    violations.append(f"""{location} has paired flags {parameter.secondary_opts}""")
                if parameter.is_bool_flag and parameter.default is True:
                    violations.append(f"""{location} has an inert default-on flag""")
                shorts = {flag for flag in parameter.opts if len(flag) == 2 and flag[0] == "-" and flag[1].isalpha()}
                if not shorts:
                    violations.append(f"""{location} has no letter shortcut""")
                if shorts.intersection(used_shorts):
                    violations.append(f"""{location} repeats a letter shortcut""")
                used_shorts.update(shorts)
            if isinstance(command, TyperGroup):
                pending_commands.extend(
                    (f"""{command_path} {name}""", child) for name, child in command.commands.items() if not child.hidden
                )
    assert violations == []


@pytest.mark.parametrize(
    ("module_name", "arguments", "deferred_modules"),
    [
        (
            "stackops.scripts.python.cloud", ["--help"],
            ("stackops.utils.cloud.rclone", "stackops.utils.cloud.onedrive.auth", "stackops.utils.cloud.onedrive.items"),
        ),
        (
            "stackops.scripts.python.preview", ["--help"],
            ("stackops.scripts.python.helpers.helpers_preview.preview_impl",),
        ),
        (
            "stackops.scripts.python.devops", ["data", "--help"],
            ("stackops.scripts.python.helpers.helpers_cloud.backup_config", "stackops.utils.files.compression"),
        ),
        (
            "stackops.scripts.python.agents", ["browser", "--help"],
            ("stackops.scripts.python.helpers.helpers_agents.agents_browser_launch", "stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output"),
        ),
    ],
)
def test_help_defers_command_implementations(module_name: str, arguments: list[str], deferred_modules: tuple[str, ...]) -> None:
    code = f"""
import importlib
import sys

module = importlib.import_module({module_name!r})
sys.argv = [{module_name!r}, *{arguments!r}]
try:
    module.main()
except SystemExit as error:
    assert error.code == 0, error.code
loaded = set({deferred_modules!r}).intersection(sys.modules)
assert not loaded, loaded
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
