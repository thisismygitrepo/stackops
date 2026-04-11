import machineconfig.scripts.python.graph as graph_assets

from machineconfig.utils.path_reference import get_path_reference_path

DEFAULT_GRAPH_PATH = get_path_reference_path(
    module=graph_assets,
    path_reference=graph_assets.CLI_GRAPH_PATH_REFERENCE,
)
