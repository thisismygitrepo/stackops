from typing import Any

from stackops.scripts.python.graph.cli_graph_apps import load_app_model
from stackops.scripts.python.graph.cli_graph_nodes import build_children
from stackops.scripts.python.graph.cli_graph_shared import AppRef, ROOT_FACTORY, ROOT_MODULE


def build_cli_graph() -> dict[str, Any]:
    root_ref = AppRef(module=ROOT_MODULE, factory=ROOT_FACTORY)
    root_model = load_app_model(root_ref)

    root_source = {
        "file": root_model.module_info.relative_path(),
        "module": root_ref.module,
        "app_factory": f"{root_ref.module}.{root_ref.factory}",
    }

    root_node: dict[str, Any] = {
        "kind": "root",
        "name": "stackops",
        "fullPath": "",
        "shortPath": "",
        "help": root_model.app_config.get("help") or "StackOps CLI",
        "source": root_source,
        "app": root_model.app_config,
        "children": build_children(
            app_model=root_model,
            parent_full_tokens=(),
            parent_short_tokens=(),
        ),
    }

    return {
        "schema": {
            "version": "1.0",
            "description": (
                "Hierarchical CLI graph for the StackOps Typer-based CLI. "
                "Nodes capture command groups and leaf commands; aliases are stored "
                "on nodes rather than separate alias nodes."
            ),
            "node": {
                "kind": "root | group | command",
                "name": "CLI token for this node",
                "fullPath": "Space-separated command path excluding the root entry token",
                "shortPath": (
                    "Space-separated command path using the shortest alias token per "
                    "segment when available"
                ),
                "help": "Command help string as registered on parent (if any)",
                "short_help": "Short help string (if set)",
                "doc": "Docstring text for leaf commands or wrapper functions",
                "aliases": "List of alias objects with name/hidden/help/short_help",
                "source": "Where the callable or Typer app is defined",
                "registered_in": "Where the command was registered if different from source",
                "command_context_settings": "Typer context_settings used when registering the command",
                "app": "Typer app configuration for groups",
                "typer": "Typer command configuration for leaf commands",
                "signature": (
                    "Structured signature object for leaf commands; includes raw_lines, "
                    "parsed parameters, and return type."
                ),
                "children": "Nested subcommands",
            },
        },
        "meta": {
            "root_entrypoint": root_model.module_info.relative_path(),
            "notes": [
                "Graph derived from static source inspection of Typer app factories and lazy wrapper dispatchers.",
                "Aliases are recorded on each node with hidden flags; no standalone alias nodes.",
                "fullPath and shortPath are root-relative command strings, excluding the 'stackops' entry token.",
                "Signature objects preserve raw lines while parsing Annotated/Option/Argument metadata into structured parameters.",
            ],
        },
        "root": root_node,
    }