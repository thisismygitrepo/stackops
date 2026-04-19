

import json

from stackops.scripts.python.graph.visualize.graph_paths import DEFAULT_GRAPH_PATH


def test_default_graph_path_points_to_existing_json_graph() -> None:
    assert DEFAULT_GRAPH_PATH.is_file()

    graph = json.loads(DEFAULT_GRAPH_PATH.read_text(encoding="utf-8"))

    assert isinstance(graph, dict)
    assert "root" in graph
