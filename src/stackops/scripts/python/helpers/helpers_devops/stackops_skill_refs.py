from collections.abc import Mapping
from datetime import date
import json
from pathlib import Path
import tomllib
from typing import Any

from stackops.scripts.python.helpers.helpers_devops import cli_self_docs


STACKOPS_SKILL_REFERENCES_RELATIVE_PATH = Path("skills", "stackops", "references")
STACKOPS_SKILL_CLI_MAP_RELATIVE_PATH = STACKOPS_SKILL_REFERENCES_RELATIVE_PATH.joinpath("cli-map.md")
STACKOPS_SKILL_SOURCE_MAP_RELATIVE_PATH = STACKOPS_SKILL_REFERENCES_RELATIVE_PATH.joinpath("source-map.md")

TREE_TEE = "\u251c\u2500 "
TREE_LAST = "\u2514\u2500 "
TREE_PIPE = "\u2502  "
TREE_SPACE = "   "


def read_cli_graph_payload(*, repo_root: Path) -> Mapping[str, Any]:
    graph_path = repo_root.joinpath(cli_self_docs.CLI_GRAPH_RELATIVE_PATH)
    if not graph_path.is_file():
        raise FileNotFoundError(f"CLI graph snapshot not found: {graph_path.relative_to(repo_root).as_posix()}")
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"CLI graph payload must be a JSON object: {graph_path.relative_to(repo_root).as_posix()}")
    return payload


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


def write_stackops_skill_references(*, repo_root: Path, generated_on: date | None = None) -> tuple[Path, Path]:
    graph_payload = read_cli_graph_payload(repo_root=repo_root)
    project_scripts = read_project_scripts(repo_root=repo_root)
    resolved_generated_on = date.today() if generated_on is None else generated_on

    cli_map_path = repo_root.joinpath(STACKOPS_SKILL_CLI_MAP_RELATIVE_PATH)
    source_map_path = repo_root.joinpath(STACKOPS_SKILL_SOURCE_MAP_RELATIVE_PATH)
    cli_map_path.parent.mkdir(parents=True, exist_ok=True)
    cli_map_path.write_text(
        render_cli_map(cli_graph_payload=graph_payload, project_scripts=project_scripts, generated_on=resolved_generated_on),
        encoding="utf-8",
    )
    source_map_path.write_text(
        render_source_map(cli_graph_payload=graph_payload, generated_on=resolved_generated_on),
        encoding="utf-8",
    )
    return cli_map_path, source_map_path


def render_cli_map(*, cli_graph_payload: Mapping[str, Any], project_scripts: Mapping[str, str], generated_on: date) -> str:
    root = _root_node(cli_graph_payload)
    lines = [
        "# StackOps CLI Map",
        "",
        f"Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on {generated_on.isoformat()}.",
        "",
        "This reference intentionally uses:",
        "- direct commands only",
        "- canonical command names only",
        "",
        "This reference intentionally excludes:",
        "- short aliases",
        "- hidden alias-only paths",
        "",
        "The tree is root-relative: use `devops repos sync` directly, or `stackops devops repos sync` through the umbrella entrypoint.",
        "",
        "## Direct Entry Points",
        "",
        "Defined in `pyproject.toml` `[project.scripts]`:",
        "",
    ]
    if len(project_scripts) == 0:
        lines.append("- No direct entry points found.")
    else:
        lines.extend(f"- `{script_name}` -> `{script_target}`" for script_name, script_target in project_scripts.items())

    lines.extend(
        [
            "",
            "## Command Tree",
            "",
            "```text",
        ]
    )
    lines.extend(_render_tree(root))
    lines.extend(
        [
            "```",
            "",
            "## Important Nuances",
            "",
            "- `devops self docs`, `devops self build-docker`, `devops self build-assets`, and `devops self workflows` are registered only when the developer checkout exists at `~/code/stackops`.",
            "- Callback groups such as `utils pyproject type-fix` and `utils pyproject test-runtime` are invoked as the group command itself.",
            "- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.",
            "- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.",
            "",
        ]
    )
    return "\n".join(lines)


def render_source_map(*, cli_graph_payload: Mapping[str, Any], generated_on: date) -> str:
    root = _root_node(cli_graph_payload)
    root_source = _source(root)
    lines = [
        "# StackOps Source Map",
        "",
        f"Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on {generated_on.isoformat()}.",
        "",
        "Use this map to jump from a command path to the file that registers or implements it. For signatures, options, aliases, and full node metadata, inspect `src/stackops/scripts/python/graph/cli_graph.json`.",
        "",
        "## Root Entrypoints",
        "",
        f"- Umbrella entrypoint: `{root_source.get('file', 'unknown')}`",
    ]
    lines.extend(_format_root_entrypoint(child) for child in _children(root))
    lines.extend(["", "## Group Routes", ""])
    group_lines = [_format_group_route(node) for node in _iter_nodes(root) if node is not root and node.get("kind") == "group"]
    lines.extend(group_lines if len(group_lines) > 0 else ["- No group routes found."])

    lines.extend(["", "## Command Implementations", ""])
    command_lines = [_format_command_implementation(node) for node in _iter_nodes(root) if node.get("kind") == "command"]
    lines.extend(command_lines if len(command_lines) > 0 else ["- No command implementations found."])

    lines.extend(
        [
            "",
            "## Debugging and Validation Workflow",
            "",
            "1. Confirm command registration in the nearest `get_app()` file from the group route above.",
            "2. Trace leaf behavior from the command implementation line above.",
            "3. Validate help surface locally with `UV_CACHE_DIR=/tmp/uv-cache uv run <command> --help` and then drill down one level at a time.",
            "4. If command names change, run `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets update-skill-refs`.",
            "",
        ]
    )
    return "\n".join(lines)


def _root_node(cli_graph_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    root = cli_graph_payload.get("root")
    if not isinstance(root, Mapping):
        raise ValueError("CLI graph payload is missing a root object")
    return root


def _children(node: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    children = node.get("children", ())
    if not isinstance(children, list):
        return ()
    return tuple(child for child in children if isinstance(child, Mapping))


def _source(node: Mapping[str, Any]) -> Mapping[str, Any]:
    source = node.get("source", {})
    if not isinstance(source, Mapping):
        return {}
    return source


def _iter_nodes(root: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    nodes: list[Mapping[str, Any]] = []

    def visit(node: Mapping[str, Any]) -> None:
        nodes.append(node)
        for child in _children(node):
            visit(child)

    visit(root)
    return tuple(nodes)


def _render_tree(root: Mapping[str, Any]) -> list[str]:
    lines = [str(root.get("name", "stackops"))]
    children = _children(root)
    for index, child in enumerate(children):
        _append_tree_node(lines=lines, node=child, prefix="", is_last=index == len(children) - 1)
    return lines


def _append_tree_node(*, lines: list[str], node: Mapping[str, Any], prefix: str, is_last: bool) -> None:
    connector = TREE_LAST if is_last else TREE_TEE
    lines.append(f"{prefix}{connector}{_tree_node_label(node)}")

    children = _children(node)
    child_prefix = prefix + (TREE_SPACE if is_last else TREE_PIPE)
    for index, child in enumerate(children):
        _append_tree_node(lines=lines, node=child, prefix=child_prefix, is_last=index == len(children) - 1)


def _tree_node_label(node: Mapping[str, Any]) -> str:
    label = str(node.get("name", ""))
    if node.get("kind") == "group" and len(_children(node)) == 0:
        return f"{label} (callback group)"
    return label


def _format_root_entrypoint(node: Mapping[str, Any]) -> str:
    name = str(node.get("name", "unknown"))
    return f"- `{name}` -> {_format_source_route(node)}"


def _format_group_route(node: Mapping[str, Any]) -> str:
    full_path = str(node.get("fullPath", node.get("name", "unknown")))
    return f"- `{full_path}` -> {_format_source_route(node)}"


def _format_command_implementation(node: Mapping[str, Any]) -> str:
    full_path = str(node.get("fullPath", node.get("name", "unknown")))
    source = _source(node)
    source_file = str(source.get("file", "unknown"))
    callable_name = str(source.get("callable", "unknown"))
    return f"- `{full_path}` -> `{source_file}` -> `{callable_name}`"


def _format_source_route(node: Mapping[str, Any]) -> str:
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
