"""
Command tree widget for displaying command hierarchy.
"""

from typing import cast

from textual.widgets import Tree
from textual.widgets.tree import TreeNode

from machineconfig.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader import (
    CommandNode,
    build_command_nodes,
    load_cli_graph,
)
from machineconfig.scripts.python.graph.visualize.helpers_navigator.data_models import CommandInfo


class CommandTree(Tree[CommandInfo]):
    """Tree widget for displaying command hierarchy."""

    def on_mount(self) -> None:
        """Build the command tree when mounted."""
        self.show_root = False
        self.guide_depth = 2
        self._build_command_tree()

    def _build_command_tree(self) -> None:
        """Build the hierarchical command structure from the CLI graph."""
        try:
            graph = load_cli_graph()
            nodes = build_command_nodes(graph)
        except Exception as exc:
            self.root.add(f"Error loading CLI graph: {exc}", data=None)
            return

        for node in nodes:
            self._add_command_node(self.root, node)

    def _add_command_node(self, parent: object, node: CommandNode) -> None:
        tree_parent = cast(TreeNode[CommandInfo], parent)
        label = self._format_label(node.info)
        tree_node = tree_parent.add(label, data=node.info)
        for child in node.children:
            self._add_command_node(tree_node, child)

    def _format_label(self, info: CommandInfo) -> str:
        if info.description and info.description != info.name:
            return f"{info.name} - {info.description}"
        return info.name
