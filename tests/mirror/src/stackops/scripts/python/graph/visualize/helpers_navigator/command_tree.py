

from pytest import MonkeyPatch

from stackops.scripts.python.graph.visualize.helpers_navigator.cli_graph_loader import (
    CommandNode,
)
from stackops.scripts.python.graph.visualize.helpers_navigator.command_tree import (
    CommandTree,
)
from stackops.scripts.python.graph.visualize.helpers_navigator.data_models import (
    CommandInfo,
)


class CommandTreeHarness(CommandTree):
    def build_command_tree_for_test(self) -> None:
        self._build_command_tree()

    def add_command_node_for_test(self, node: CommandNode) -> None:
        self._add_command_node(self.root, node)


def test_build_command_tree_surfaces_load_failures(monkeypatch: MonkeyPatch) -> None:
    tree = CommandTreeHarness("stackops commands")

    def explode() -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "stackops.scripts.python.graph.visualize.helpers_navigator.command_tree.load_cli_graph",
        explode,
    )

    tree.build_command_tree_for_test()

    assert len(tree.root.children) == 1
    assert str(tree.root.children[0].label) == "Error loading CLI graph: boom"
    assert tree.root.children[0].data is None


def test_add_command_node_recurses_and_formats_labels() -> None:
    tree = CommandTreeHarness("stackops commands")
    root_command = CommandNode(
        info=CommandInfo(
            name="graph",
            description="Graph tools",
            command="graph",
            is_group=True,
        ),
        children=[
            CommandNode(
                info=CommandInfo(
                    name="render",
                    description="render",
                    command="graph render",
                ),
                children=[],
            )
        ],
    )

    tree.add_command_node_for_test(root_command)

    root_child = tree.root.children[0]
    nested_child = root_child.children[0]

    assert str(root_child.label) == "graph - Graph tools"
    assert root_child.data is root_command.info
    assert str(nested_child.label) == "render"
    assert nested_child.data is root_command.children[0].info
