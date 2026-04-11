from pathlib import Path
import machineconfig.scripts.python.graph as graph_assets

from machineconfig.scripts.python.graph import CLI_GRAPH_PATH_REFERENCE
from machineconfig.utils.path_reference import get_path_reference_path

DEFAULT_GRAPH_PATH = get_path_reference_path(module=graph_assets, path_reference=CLI_GRAPH_PATH_REFERENCE)
