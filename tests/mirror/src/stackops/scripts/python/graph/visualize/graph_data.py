import json
from pathlib import Path

import stackops.scripts.python.graph.visualize.graph_data as target


def _write_graph(tmp_path: Path) -> Path:
    graph_path = tmp_path / "cli_graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "root": {
                    "kind": "root",
                    "name": "stackops",
                    "help": "StackOps CLI",
                    "children": [
                        {
                            "kind": "group",
                            "name": "graph",
                            "app": {"help": "Graph tools"},
                            "aliases": [{"name": "g"}],
                            "children": [
                                {
                                    "kind": "command",
                                    "name": "search",
                                    "short_help": "Find commands",
                                },
                                {
                                    "kind": "command",
                                    "name": "dot",
                                    "help": "Export graphviz dot",
                                },
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    return graph_path


def test_build_graph_builds_aliases_descriptions_and_leaf_counts(
    tmp_path: Path,
) -> None:
    graph = target.build_graph(path=str(_write_graph(tmp_path)))
    group = graph.children[0]
    search = group.children[0]
    dot = group.children[1]

    assert graph.id == "stackops"
    assert graph.leaf_count == 2
    assert group.aliases == ["g"]
    assert group.description == "Graph tools"
    assert search.description == "Find commands"
    assert dot.long_description == "Export graphviz dot"


def test_iter_nodes_walks_preorder(tmp_path: Path) -> None:
    graph = target.build_graph(path=str(_write_graph(tmp_path)))

    ids = [node.id for node, _parent in target.iter_nodes(graph)]

    assert ids == [
        "stackops",
        "stackops graph",
        "stackops graph search",
        "stackops graph dot",
    ]
