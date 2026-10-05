from collections.abc import Callable
from importlib import import_module
import subprocess
import sys
from typing import NotRequired, TypedDict, cast

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


def test_registered_options_have_single_flags_and_distinct_letter_shortcuts() -> None:
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

    violations: list[str] = []
    for factory_path in sorted(factories):
        module_name, _, factory_name = factory_path.rpartition(".")
        factory = cast(Callable[[], typer.Typer], getattr(import_module(module_name), factory_name))
        pending_commands = [(factory_path, get_command(factory()))]
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
