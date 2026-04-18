from _pytest.monkeypatch import MonkeyPatch

import stackops.scripts.python.graph.visualize.dot_export as target
from stackops.scripts.python.graph.visualize.graph_data import GraphNode


def _sample_graph() -> GraphNode:
    return GraphNode(
        id="mcfg",
        name="mcfg",
        kind="root",
        command="",
        description="StackOps CLI",
        long_description="StackOps CLI",
        aliases=[],
        depth=0,
        children=[
            GraphNode(
                id="mcfg graph",
                name="graph",
                kind="group",
                command="graph",
                description="Graph tooling",
                long_description="Graph tooling",
                aliases=["g"],
                depth=1,
                children=[
                    GraphNode(
                        id="mcfg graph search",
                        name='search "nodes"',
                        kind="command",
                        command="graph search",
                        description="x" * 90,
                        long_description="x" * 90,
                        aliases=[],
                        depth=2,
                    )
                ],
            )
        ],
    )


def test_build_dot_respects_max_depth_and_edges() -> None:
    dot_text = target.build_dot(_sample_graph(), max_depth=1, include_help=False)

    assert '"mcfg"' in dot_text
    assert '"mcfg graph"' in dot_text
    assert '"mcfg" -> "mcfg graph";' in dot_text
    assert '"mcfg graph search"' not in dot_text


def test_build_dot_escapes_special_characters_and_truncates_help() -> None:
    dot_text = target.build_dot(_sample_graph(), max_depth=None, include_help=True)

    assert 'search \\"nodes\\"\\n' in dot_text
    assert "..." in dot_text


def test_render_dot_delegates_to_build_graph(monkeypatch: MonkeyPatch) -> None:
    sample_graph = _sample_graph()
    seen_paths: list[str | None] = []

    def build_graph(path: str | None) -> GraphNode:
        seen_paths.append(path)
        return sample_graph

    monkeypatch.setattr(target, "build_graph", build_graph)

    dot_text = target.render_dot(path="graph.json", max_depth=2, include_help=False)

    assert seen_paths == ["graph.json"]
    assert dot_text == target.build_dot(sample_graph, max_depth=2, include_help=False)
