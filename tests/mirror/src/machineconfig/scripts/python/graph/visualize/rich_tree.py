from __future__ import annotations

from rich.text import Text
from rich.tree import Tree
import pytest

from machineconfig.scripts.python.graph.visualize import rich_tree
from machineconfig.scripts.python.graph.visualize.graph_data import GraphNode


class RecordingConsole:
    def __init__(self) -> None:
        self.printed: list[object] = []

    def print(self, renderable: object) -> None:
        self.printed.append(renderable)


def _build_root() -> GraphNode:
    grandchild = GraphNode(
        id="root group leaf",
        name="leaf",
        kind="command",
        command="root group leaf",
        description="leaf help",
        long_description="leaf help",
        aliases=["leaf-alias"],
        depth=2,
        children=[],
        leaf_count=1,
    )
    child = GraphNode(
        id="root group",
        name="group",
        kind="group",
        command="root group",
        description="group help",
        long_description="group help",
        aliases=["grp"],
        depth=1,
        children=[grandchild],
        leaf_count=1,
    )
    return GraphNode(
        id="root",
        name="root",
        kind="root",
        command="root",
        description="root help",
        long_description="root help",
        aliases=[],
        depth=0,
        children=[child],
        leaf_count=1,
    )


def test_format_label_includes_help_and_aliases() -> None:
    node = GraphNode(
        id="deploy",
        name="deploy",
        kind="command",
        command="deploy",
        description="Ship release",
        long_description="Ship release",
        aliases=["ship", "release"],
        depth=0,
        children=[],
        leaf_count=1,
    )

    label = rich_tree._format_label(node, show_help=True, show_aliases=True)

    assert label.plain == "deploy - Ship release (aliases: ship, release)"


def test_build_rich_tree_respects_max_depth() -> None:
    root = _build_root()

    tree = rich_tree.build_rich_tree(root, show_help=False, show_aliases=False, max_depth=1)

    assert len(tree.children) == 1
    child_label = tree.children[0].label
    assert isinstance(child_label, Text)
    assert child_label.plain == "group"
    assert tree.children[0].children == []


def test_render_tree_prints_built_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _build_root()
    console = RecordingConsole()

    def fake_build_graph(path: str | None) -> GraphNode:
        _ = path
        return root

    def fake_console() -> RecordingConsole:
        return console

    monkeypatch.setattr(rich_tree, "build_graph", fake_build_graph)
    monkeypatch.setattr(rich_tree, "Console", fake_console)

    rich_tree.render_tree(path=None, show_help=False, show_aliases=False, max_depth=1)

    assert len(console.printed) == 1
    assert isinstance(console.printed[0], Tree)
