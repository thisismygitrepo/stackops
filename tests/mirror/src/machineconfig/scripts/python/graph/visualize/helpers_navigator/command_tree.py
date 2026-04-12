from __future__ import annotations

from machineconfig.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader import CommandNode
from machineconfig.scripts.python.graph.visualize.helpers_navigator.command_tree import CommandTree
from machineconfig.scripts.python.graph.visualize.helpers_navigator.data_models import CommandInfo


def test_build_command_tree_surfaces_load_failures(monkeypatch: object) -> None:
    tree = CommandTree("machineconfig commands")

    def explode() -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr("machineconfig.scripts.python.graph.visualize.helpers_navigator.command_tree.load_cli_graph", explode)

    tree._build_command_tree()

    assert len(tree.root.children) == 1
    assert "Error loading CLI graph: boom" in tree.root.children[0].label.plain
    assert tree.root.children[0].data is None


def test_add_command_node_recurses_and_formats_labels() -> None:
    tree = CommandTree("machineconfig commands")
    root_command = CommandNode(
        info=CommandInfo(name="graph", description="Graph tools", command="graph", is_group=True),
        children=[CommandNode(info=CommandInfo(name="render", description="render", command="graph render"), children=[])],
    )

    tree._add_command_node(tree.root, root_command)

    root_child = tree.root.children[0]
    nested_child = root_child.children[0]

    assert root_child.label.plain == "graph - Graph tools"
    assert root_child.data is root_command.info
    assert nested_child.label.plain == "render"
    assert nested_child.data is root_command.children[0].info
