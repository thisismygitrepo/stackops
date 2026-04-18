from pathlib import Path

import stackops.scripts.python.graph as target
from stackops.utils.path_reference import get_path_reference_path


def test_cli_graph_path_reference_resolves_existing_file() -> None:
    graph_path = get_path_reference_path(
        module=target,
        path_reference=target.CLI_GRAPH_PATH_REFERENCE,
    )

    module_file_text = target.__file__
    assert module_file_text is not None
    module_dir = Path(module_file_text).resolve().parent

    assert graph_path.name == "cli_graph.json"
    assert graph_path.exists()
    assert graph_path.is_file()
    assert module_dir in graph_path.resolve().parents
