from collections.abc import Mapping
from datetime import date
import json
from pathlib import Path
import shutil
import tomllib
from typing import TypeAlias, cast

from stackops.scripts.python.helpers.helpers_devops import cli_self_docs


STACKOPS_SKILL_REFERENCES_RELATIVE_PATH = Path("skills", "stackops", "references")
STACKOPS_SKILL_CLI_MAP_RELATIVE_PATH = STACKOPS_SKILL_REFERENCES_RELATIVE_PATH.joinpath("cli-map.md")
STACKOPS_SKILL_SOURCE_MAP_RELATIVE_PATH = STACKOPS_SKILL_REFERENCES_RELATIVE_PATH.joinpath("source-map.md")
STALE_STACKOPS_SKILL_COMMAND_REFERENCES_RELATIVE_PATH = STACKOPS_SKILL_REFERENCES_RELATIVE_PATH.joinpath("commands")
CLI_GRAPH_DISPLAY_PATH = "src/stackops/scripts/python/graph/cli_graph.json"
JsonObject: TypeAlias = Mapping[str, object]


def read_cli_graph_payload(*, repo_root: Path) -> JsonObject:
    graph_path = repo_root.joinpath(cli_self_docs.CLI_GRAPH_RELATIVE_PATH)
    if not graph_path.is_file():
        raise FileNotFoundError(f"CLI graph snapshot not found: {graph_path.relative_to(repo_root).as_posix()}")
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"CLI graph payload must be a JSON object: {graph_path.relative_to(repo_root).as_posix()}")
    return cast(JsonObject, payload)


def read_project_scripts(*, repo_root: Path) -> Mapping[str, str]:
    pyproject_path = repo_root.joinpath("pyproject.toml")
    with pyproject_path.open("rb") as pyproject_file:
        pyproject_payload = tomllib.load(pyproject_file)

    project_payload = pyproject_payload.get("project", {})
    if not isinstance(project_payload, Mapping):
        return {}
    scripts_payload = project_payload.get("scripts", {})
    if not isinstance(scripts_payload, Mapping):
        return {}

    scripts: dict[str, str] = {}
    for raw_name, raw_target in scripts_payload.items():
        if isinstance(raw_name, str) and isinstance(raw_target, str):
            scripts[raw_name] = raw_target
    return scripts


def write_stackops_skill_references(*, repo_root: Path, generated_on: date | None = None) -> tuple[Path, ...]:
    graph_payload = read_cli_graph_payload(repo_root=repo_root)
    project_scripts = read_project_scripts(repo_root=repo_root)
    resolved_generated_on = date.today() if generated_on is None else generated_on

    cli_map_path = repo_root.joinpath(STACKOPS_SKILL_CLI_MAP_RELATIVE_PATH)
    source_map_path = repo_root.joinpath(STACKOPS_SKILL_SOURCE_MAP_RELATIVE_PATH)
    stale_command_references_path = repo_root.joinpath(STALE_STACKOPS_SKILL_COMMAND_REFERENCES_RELATIVE_PATH)
    cli_map_path.parent.mkdir(parents=True, exist_ok=True)
    if stale_command_references_path.exists():
        shutil.rmtree(stale_command_references_path)

    cli_map_path.write_text(
        render_cli_map(cli_graph_payload=graph_payload, project_scripts=project_scripts, generated_on=resolved_generated_on),
        encoding="utf-8",
    )
    source_map_path.write_text(
        render_source_map(cli_graph_payload=graph_payload, generated_on=resolved_generated_on),
        encoding="utf-8",
    )
    return cli_map_path, source_map_path


def render_cli_map(*, cli_graph_payload: JsonObject, project_scripts: Mapping[str, str], generated_on: date) -> str:
    root = _root_node(cli_graph_payload)
    lines = [
        "# StackOps CLI Map",
        "",
        f"Regenerated from `{CLI_GRAPH_DISPLAY_PATH}` on {generated_on.isoformat()}.",
        "",
        "Use this as a root index only. Discover command groups, options, defaults, aliases, and help text from the live CLI with `--help`.",
        "",
        "This reference intentionally excludes:",
        "- command option listings",
        "- generated per-command reference pages",
        "- short aliases",
        "- hidden alias-only paths",
        "- nested command trees",
        "",
        "Do not copy details from this file when `uv run <entrypoint> --help` can provide the current answer.",
        "",
        "## Direct Entry Points",
        "",
        "Defined in `pyproject.toml` `[project.scripts]`:",
        "",
    ]
    if len(project_scripts) == 0:
        lines.append("- No direct entry points found.")
    else:
        for script_name, script_target in project_scripts.items():
            lines.append(f"- `{script_name}` -> `{script_target}`")

    lines.extend(
        [
            "",
            "## Top-Level Help",
            "",
        ]
    )
    lines.append("- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops --help`")
    lines.extend(f"- `UV_CACHE_DIR=/tmp/uv-cache uv run {_name(child)} --help`" for child in _children(root))
    lines.extend(["", "## Important Nuances", ""])
    lines.extend(_important_nuance_lines())
    lines.append("")
    return "\n".join(lines)


def render_source_map(*, cli_graph_payload: JsonObject, generated_on: date) -> str:
    root = _root_node(cli_graph_payload)
    root_source = _source(root)
    lines = [
        "# StackOps Source Map",
        "",
        f"Regenerated from `{CLI_GRAPH_DISPLAY_PATH}` on {generated_on.isoformat()}.",
        "",
        "Use this map as a root source index. For command-level source details, inspect Typer registrations and verify the live command with `--help`.",
        "",
        "## Root Entrypoints",
        "",
        f"- Umbrella entrypoint: `{root_source.get('file', 'unknown')}`",
    ]
    lines.extend(_format_root_entrypoint(child) for child in _children(root))
    lines.extend(
        [
            "",
            "## Debugging and Validation Workflow",
            "",
            "1. Start from the relevant root entrypoint above.",
            "2. Run `UV_CACHE_DIR=/tmp/uv-cache uv run <entrypoint> --help` and then repeat with each discovered command segment.",
            "3. Inspect the Typer registration source only after the live help identifies the command path.",
            "4. For broad graph debugging, inspect `src/stackops/scripts/python/graph/cli_graph.json`.",
            "5. After changing command names or registrations, run `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets update-skill-refs`.",
            "",
        ]
    )
    return "\n".join(lines)


def _important_nuance_lines() -> list[str]:
    return [
        "- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.",
        "- Callback groups are invoked as the group command itself; confirm the exact behavior with `--help`.",
        f"- The generated graph stores aliases and metadata. Use `{CLI_GRAPH_DISPLAY_PATH}` only when live help or source is insufficient.",
        "- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.",
    ]


def _name(node: JsonObject) -> str:
    name = node.get("name")
    if isinstance(name, str) and name != "":
        return name
    return "stackops"


def _root_node(cli_graph_payload: JsonObject) -> JsonObject:
    root = cli_graph_payload.get("root")
    if not isinstance(root, Mapping):
        raise ValueError("CLI graph payload is missing a root object")
    return cast(JsonObject, root)


def _children(node: JsonObject) -> tuple[JsonObject, ...]:
    children = node.get("children", ())
    if not isinstance(children, list):
        return ()
    return tuple(cast(JsonObject, child) for child in children if isinstance(child, Mapping))


def _source(node: JsonObject) -> JsonObject:
    source = node.get("source", {})
    if not isinstance(source, Mapping):
        return {}
    return cast(JsonObject, source)


def _format_root_entrypoint(node: JsonObject) -> str:
    name = _name(node)
    return f"- `{name}` -> {_format_source_route(node)}"


def _format_source_route(node: JsonObject) -> str:
    source = _source(node)
    source_file = str(source.get("file", "unknown"))
    route_parts = [f"`{source_file}`"]
    dispatches_to = source.get("dispatches_to")
    app_factory = source.get("app_factory")
    callable_name = source.get("callable")
    if isinstance(dispatches_to, str):
        route_parts.append(f"`{dispatches_to}` via `{node.get('name', 'unknown')}`")
    elif isinstance(app_factory, str):
        route_parts.append(f"`{app_factory}`")
    elif isinstance(callable_name, str):
        route_parts.append(f"`{callable_name}`")
    return " -> ".join(route_parts)
