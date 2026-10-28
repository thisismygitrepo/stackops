from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
from typing import NotRequired, TypedDict, cast

from stackops.scripts.python.graph.cli_graph_shared import REPO_ROOT
from stackops.scripts.python.graph.cli_graph_tree import build_cli_graph


class AppSource(TypedDict):
    app_factory: NotRequired[str]
    dispatches_to: NotRequired[str]


class AppNode(TypedDict):
    source: AppSource
    children: NotRequired[list["AppNode"]]


class CliGraph(TypedDict):
    root: AppNode


FORBIDDEN_AT_BUILD_TIME: tuple[str, ...] = (
    "git",
    "rich.console",
    "rich.table",
    "rich.panel",
    "rich.text",
    "rich.progress",
    "rich.live",
    "requests",
    "urllib3",
    "httpx",
    "yaml",
    "psutil",
    "paramiko",
    "polars",
    "pandas",
    "numpy",
    "pydantic",
    "cryptography",
    "questionary",
    "pyperclip",
    "duckdb",
    "tomlkit",
    "toml",
)

PROBE_SCRIPT = """
import importlib
import json
import sys

import typer.main

module_name, _, factory_name = sys.argv[1].rpartition(".")
typer.main.get_command(getattr(importlib.import_module(module_name), factory_name)())
print(json.dumps([name for name in json.loads(sys.argv[2]) if name in sys.modules]))
"""


def _factory_paths() -> list[str]:
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
    return sorted(factories)


def _loaded_modules(factory_path: str, candidates: tuple[str, ...]) -> list[str]:
    environment = {**os.environ, "PYTHONPATH": REPO_ROOT.joinpath("src").as_posix()}
    result = subprocess.run(
        [sys.executable, "-c", PROBE_SCRIPT, factory_path, json.dumps(candidates)],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=environment,
        check=False,
    )
    assert result.returncode == 0, f"""{factory_path} failed to build:\n{result.stderr}"""
    return cast(list[str], json.loads(result.stdout.strip().splitlines()[-1]))


def test_probe_reports_modules_that_are_loaded() -> None:
    factory_path = _factory_paths()[0]

    assert _loaded_modules(factory_path, ("typer.main",)) == ["typer.main"]


def test_building_any_command_group_does_not_import_heavy_modules() -> None:
    factory_paths = _factory_paths()
    assert factory_paths

    with ThreadPoolExecutor(max_workers=8) as pool:
        loaded = list(pool.map(lambda path: _loaded_modules(path, FORBIDDEN_AT_BUILD_TIME), factory_paths))

    violations = [f"""{path} imports {modules} while being built""" for path, modules in zip(factory_paths, loaded, strict=True) if modules]
    assert violations == []
