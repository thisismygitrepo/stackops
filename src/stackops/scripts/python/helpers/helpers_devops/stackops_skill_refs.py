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
STACKOPS_SKILL_COMMAND_REFERENCES_RELATIVE_PATH = STACKOPS_SKILL_REFERENCES_RELATIVE_PATH.joinpath("commands")
CLI_GRAPH_DISPLAY_PATH = "src/stackops/scripts/python/graph/cli_graph.json"


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


def write_stackops_skill_references(*, repo_root: Path, generated_on: date | None = None) -> tuple[Path, ...]:
    graph_payload = read_cli_graph_payload(repo_root=repo_root)
    project_scripts = read_project_scripts(repo_root=repo_root)
    resolved_generated_on = date.today() if generated_on is None else generated_on

    cli_map_path = repo_root.joinpath(STACKOPS_SKILL_CLI_MAP_RELATIVE_PATH)
    source_map_path = repo_root.joinpath(STACKOPS_SKILL_SOURCE_MAP_RELATIVE_PATH)
    command_references_path = repo_root.joinpath(STACKOPS_SKILL_COMMAND_REFERENCES_RELATIVE_PATH)
    cli_map_path.parent.mkdir(parents=True, exist_ok=True)
    command_references_path.mkdir(parents=True, exist_ok=True)
    for stale_reference_path in command_references_path.glob("*.md"):
        stale_reference_path.unlink()

    cli_map_path.write_text(
        render_cli_map(cli_graph_payload=graph_payload, project_scripts=project_scripts, generated_on=resolved_generated_on),
        encoding="utf-8",
    )
    source_map_path.write_text(
        render_source_map(cli_graph_payload=graph_payload, generated_on=resolved_generated_on),
        encoding="utf-8",
    )
    generated_paths = [cli_map_path, source_map_path]
    for relative_path, reference_text in render_command_references(
        cli_graph_payload=graph_payload,
        generated_on=resolved_generated_on,
    ).items():
        reference_path = repo_root.joinpath(relative_path)
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_text(reference_text, encoding="utf-8")
        generated_paths.append(reference_path)
    return tuple(generated_paths)


def render_cli_map(*, cli_graph_payload: Mapping[str, Any], project_scripts: Mapping[str, str], generated_on: date) -> str:
    root = _root_node(cli_graph_payload)
    lines = [
        "# StackOps CLI Map",
        "",
        f"Regenerated from `{CLI_GRAPH_DISPLAY_PATH}` on {generated_on.isoformat()}.",
        "",
        "This reference intentionally uses:",
        "- direct commands only",
        "- canonical command names only",
        "- one-level command expansion through linked command reference files",
        "",
        "This reference intentionally excludes:",
        "- short aliases",
        "- hidden alias-only paths",
        "- nested command trees",
        "",
        "Open exactly the next command reference you need instead of loading the full CLI tree.",
        "",
        "## Direct Entry Points",
        "",
        "Defined in `pyproject.toml` `[project.scripts]`:",
        "",
    ]
    top_level_nodes = _top_level_nodes_by_name(root)
    if len(project_scripts) == 0:
        lines.append("- No direct entry points found.")
    else:
        for script_name, script_target in project_scripts.items():
            reference_node = root if script_name == "stackops" else top_level_nodes.get(script_name)
            reference_suffix = "" if reference_node is None else f". Reference: {_reference_link_from_index(reference_node)}"
            lines.append(f"- `{script_name}` -> `{script_target}`{reference_suffix}")

    lines.extend(
        [
            "",
            "## Top-Level Command References",
            "",
        ]
    )
    lines.append(f"- {_reference_link_from_index(root)} - umbrella dispatcher and root source.")
    lines.extend(_format_index_child_line(child) for child in _children(root))
    lines.extend(["", "## Important Nuances", ""])
    lines.extend(_important_nuance_lines())
    lines.append("")
    return "\n".join(lines)


def render_source_map(*, cli_graph_payload: Mapping[str, Any], generated_on: date) -> str:
    root = _root_node(cli_graph_payload)
    root_source = _source(root)
    lines = [
        "# StackOps Source Map",
        "",
        f"Regenerated from `{CLI_GRAPH_DISPLAY_PATH}` on {generated_on.isoformat()}.",
        "",
        "Use this map as the root source index. Command-level source details live in the linked one-level command references.",
        "",
        "## Root Entrypoints",
        "",
        f"- Umbrella entrypoint: `{root_source.get('file', 'unknown')}`. Reference: {_reference_link_from_index(root)}",
    ]
    lines.extend(_format_root_entrypoint(child) for child in _children(root))
    lines.extend(
        [
            "",
            "## Debugging and Validation Workflow",
            "",
            "1. Open the command reference for the current command segment.",
            "2. Confirm command registration from the current page source route.",
            "3. Follow only the next child reference when a deeper command segment is needed.",
            "4. Validate help surface locally with `UV_CACHE_DIR=/tmp/uv-cache uv run <command> --help`.",
            "5. If command names change, follow the `devops` reference chain to the generated-reference maintenance command.",
            "",
        ]
    )
    return "\n".join(lines)


def render_command_references(*, cli_graph_payload: Mapping[str, Any], generated_on: date) -> dict[Path, str]:
    root = _root_node(cli_graph_payload)
    references: dict[Path, str] = {}
    for node in _iter_nodes(root):
        references[_reference_relative_path(node)] = render_command_reference(node=node, generated_on=generated_on)
    return references


def render_command_reference(*, node: Mapping[str, Any], generated_on: date) -> str:
    command_path = _command_path(node)
    children = _children(node)
    lines = [
        f"# StackOps Command Reference: `{command_path}`",
        "",
        f"Regenerated from `{CLI_GRAPH_DISPLAY_PATH}` on {generated_on.isoformat()}.",
        "",
        f"This page expands exactly one level below `{command_path}`. Follow child links one command segment at a time.",
        "",
        "## Current Command",
        "",
        f"- Path: `{command_path}`",
        f"- Kind: `{_kind(node)}`",
        f"- Source: {_format_source_route(node)}",
    ]
    help_text = _help_text(node)
    if help_text != "":
        lines.append(f"- Help: `{help_text}`")
    lines.extend(["", "## Help Commands", ""])
    lines.extend(f"- `{help_command}`" for help_command in _help_commands(node))
    lines.extend(["", "## Immediate Children", ""])
    if len(children) == 0:
        lines.append(
            f"- No child command references. Use `UV_CACHE_DIR=/tmp/uv-cache uv run {command_path} --help` for options and inspect `{CLI_GRAPH_DISPLAY_PATH}` for full metadata."
        )
    else:
        lines.extend(_format_child_reference_line(child) for child in children)
    lines.extend(
        [
            "",
            "## Notes",
            "",
        ]
    )
    lines.extend(_notes_for_node(node))
    lines.append("")
    return "\n".join(lines)


def _top_level_nodes_by_name(root: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {_name(child): child for child in _children(root)}


def _important_nuance_lines() -> list[str]:
    return [
        "- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.",
        "- Callback groups are invoked as the group command itself when their command reference has no children.",
        f"- The generated graph stores aliases on each node. Use `{CLI_GRAPH_DISPLAY_PATH}` when alias details matter.",
        "- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.",
    ]


def _notes_for_node(node: Mapping[str, Any]) -> list[str]:
    notes = _important_nuance_lines()
    if _kind(node) == "group" and len(_children(node)) == 0:
        notes.insert(0, "- This is a callback group, so the group path is the invocable command.")
    return notes


def _format_index_child_line(node: Mapping[str, Any]) -> str:
    return f"- {_reference_link_from_index(node)} - {_node_shape_label(node)}."


def _reference_link_from_index(node: Mapping[str, Any]) -> str:
    label = _command_path(node)
    path = Path("commands").joinpath(_reference_file_name(node))
    return f"[`{label}`]({path.as_posix()})"


def _reference_link_from_command_page(node: Mapping[str, Any]) -> str:
    return f"[`{_command_path(node)}`]({_reference_file_name(node)})"


def _reference_relative_path(node: Mapping[str, Any]) -> Path:
    return STACKOPS_SKILL_COMMAND_REFERENCES_RELATIVE_PATH.joinpath(_reference_file_name(node))


def _reference_file_name(node: Mapping[str, Any]) -> str:
    return f"command--{_command_path(node).replace(' ', '--')}.md"


def _format_child_reference_line(node: Mapping[str, Any]) -> str:
    line = f"- {_reference_link_from_command_page(node)} - {_node_shape_label(node)}"
    help_text = _help_text(node)
    if help_text != "":
        line = f"{line}. Help: `{help_text}`"
    return f"{line}."


def _node_shape_label(node: Mapping[str, Any]) -> str:
    child_count = len(_children(node))
    kind = _kind(node)
    if kind == "group" and child_count == 0:
        return "callback group with no child commands"
    if child_count == 0:
        return f"{kind} with no child commands"
    child_label = "child command" if child_count == 1 else "child commands"
    return f"{kind} with {child_count} immediate {child_label}"


def _help_commands(node: Mapping[str, Any]) -> tuple[str, ...]:
    command_path = _command_path(node)
    if command_path == "stackops":
        return ("UV_CACHE_DIR=/tmp/uv-cache uv run stackops --help",)
    return (
        f"UV_CACHE_DIR=/tmp/uv-cache uv run {command_path} --help",
        f"UV_CACHE_DIR=/tmp/uv-cache uv run stackops {command_path} --help",
    )


def _command_path(node: Mapping[str, Any]) -> str:
    full_path = node.get("fullPath")
    if isinstance(full_path, str) and full_path != "":
        return full_path
    return _name(node)


def _name(node: Mapping[str, Any]) -> str:
    name = node.get("name")
    if isinstance(name, str) and name != "":
        return name
    return "stackops"


def _kind(node: Mapping[str, Any]) -> str:
    kind = node.get("kind")
    if isinstance(kind, str) and kind != "":
        return kind
    return "unknown"


def _help_text(node: Mapping[str, Any]) -> str:
    help_text = node.get("help")
    if isinstance(help_text, str):
        return help_text.replace("`", "'")
    return ""


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


def _format_root_entrypoint(node: Mapping[str, Any]) -> str:
    name = _name(node)
    return f"- `{name}` -> {_format_source_route(node)}. Reference: {_reference_link_from_index(node)}"


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
