

from pathlib import Path
from typing import Any

from stackops.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader import build_command_nodes, load_cli_graph


def test_load_cli_graph_reads_explicit_file(tmp_path: Path) -> None:
    graph_path = tmp_path.joinpath("graph.json")
    graph_path.write_text("""{"root": {"children": []}}""", encoding="utf-8")

    loaded_graph = load_cli_graph(graph_path)

    assert loaded_graph == {"root": {"children": []}}


def test_build_command_nodes_normalizes_commands_arguments_and_usage() -> None:
    graph: dict[str, Any] = {
        "root": {
            "name": "stackops",
            "children": [
                {
                    "name": "graph",
                    "kind": "group",
                    "app": {"help": "Graph tools"},
                    "source": {"module": "stackops.graph"},
                    "children": [
                        {
                            "name": "render",
                            "short_help": "Render graph",
                            "help": "Render graph to file",
                            "source": {"dispatches_to": "stackops.graph.render"},
                            "signature": {
                                "parameters": [
                                    {"name": "target", "required": True, "typer": {"kind": "argument", "help": "Target graph"}},
                                    {
                                        "name": "verbose",
                                        "required": False,
                                        "type": "bool",
                                        "typer": {
                                            "kind": "option",
                                            "help": "Verbose mode",
                                            "long_flags": ["--verbose", "--no-verbose"],
                                            "short_flags": ["-v"],
                                            "param_decls": ["--verbose/--no-verbose"],
                                        },
                                    },
                                    {
                                        "name": "format",
                                        "required": False,
                                        "type": "str",
                                        "typer": {"kind": "option", "help": "Output format", "long_flags": ["--format"], "short_flags": ["-f"]},
                                    },
                                ]
                            },
                        }
                    ],
                }
            ],
        }
    }

    nodes_without_root = build_command_nodes(graph)
    nodes_with_root = build_command_nodes(graph, include_root=True)

    assert len(nodes_without_root) == 1
    group_node = nodes_without_root[0]
    assert group_node.info.is_group
    assert group_node.info.command == "graph"
    assert group_node.info.description == "Graph tools"
    assert group_node.info.long_description == "Graph tools"
    assert group_node.info.module_path == "stackops.graph"

    command_node = group_node.children[0]
    assert command_node.info.command == "graph render"
    assert command_node.info.parent == "graph"
    assert command_node.info.description == "Render graph"
    assert command_node.info.long_description == "Render graph to file"
    assert command_node.info.module_path == "stackops.graph.render"
    assert command_node.info.help_text == "graph render <target> [--verbose|--no-verbose] [--format <format>]"

    assert command_node.info.arguments is not None
    assert [argument.name for argument in command_node.info.arguments] == ["target", "verbose", "format"]

    target, verbose, fmt = command_node.info.arguments
    assert target.is_positional
    assert target.is_required
    assert target.description == "Target graph"

    assert verbose.is_flag
    assert verbose.flag == "--verbose"
    assert verbose.negated_flag == "--no-verbose"
    assert verbose.long_flags == ["--verbose", "--no-verbose"]
    assert verbose.short_flags == ["-v"]

    assert not fmt.is_flag
    assert fmt.flag == "--format"
    assert fmt.short_flags == ["-f"]

    assert nodes_with_root[0].info.command == "stackops graph"
    assert nodes_with_root[0].children[0].info.command == "stackops graph render"


def test_build_command_nodes_uses_fallback_flag_for_option_without_declared_flags() -> None:
    graph: dict[str, Any] = {
        "root": {
            "children": [
                {
                    "name": "check",
                    "signature": {
                        "parameters": [{"name": "cache_path", "required": False, "type": "str", "typer": {"kind": "option", "help": "Cache path"}}]
                    },
                }
            ]
        }
    }

    command_node = build_command_nodes(graph)[0]

    assert command_node.info.help_text == "check [--cache-path <cache_path>]"
    assert command_node.info.arguments is not None
    assert command_node.info.arguments[0].flag == "--cache-path"
