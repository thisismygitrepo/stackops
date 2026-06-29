import json
import re
from typing import cast

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_graph import (
    edge_node_names,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
)

_PYAN_NODE_PATTERN = re.compile(r'^\s*"(?P<node_id>[^"]+)" \[.*tooltip="(?P<tooltip>[^"]+)"')
_PYAN_EDGE_PATTERN = re.compile(r'^\s*"(?P<importer>[^"]+)" -> "(?P<imported>[^"]+)"')


def parse_pyan_dot(dot_output: str) -> DependencyGraph:
    node_names_by_id: dict[str, str] = {}
    for line in dot_output.splitlines():
        node_match = _PYAN_NODE_PATTERN.match(line)
        if node_match is not None:
            node_id = node_match.group("node_id")
            tooltip = node_match.group("tooltip")
            node_names_by_id[node_id] = tooltip.split("\\n", maxsplit=1)[0]
    edges: set[DependencyEdge] = set()
    for line in dot_output.splitlines():
        edge_match = _PYAN_EDGE_PATTERN.match(line)
        if edge_match is None:
            continue
        importer_id = edge_match.group("importer")
        imported_id = edge_match.group("imported")
        importer = node_names_by_id.get(importer_id, importer_id.replace("__", "."))
        imported = node_names_by_id.get(imported_id, imported_id.replace("__", "."))
        edges.add(DependencyEdge(importer=importer, imported=imported))
    nodes = tuple(
        sorted(
            DependencyNode(name=name, path=None)
            for name in set(node_names_by_id.values()) | edge_node_names(edges)
        )
    )
    return DependencyGraph(nodes=nodes, edges=tuple(sorted(edges)))


def parse_pydeps_json(stdout: str) -> DependencyGraph:
    json_text = _extract_json_object_text(text=stdout)
    raw_payload = cast(dict[str, object], json.loads(json_text))
    node_names: set[str] = set()
    edges: set[DependencyEdge] = set()
    path_by_node: dict[str, str | None] = {}
    for node_name, raw_node in raw_payload.items():
        if isinstance(raw_node, dict) is False:
            continue
        raw_node_dict = cast(dict[str, object], raw_node)
        node_names.add(node_name)
        path_by_node[node_name] = _read_optional_string(raw_node_dict.get("path"))
        imports = _read_string_tuple(raw_node_dict.get("imports"))
        for imported in imports:
            node_names.add(imported)
            edges.add(DependencyEdge(importer=node_name, imported=imported))
        imported_by = _read_string_tuple(raw_node_dict.get("imported_by"))
        for importer in imported_by:
            node_names.add(importer)
            edges.add(DependencyEdge(importer=importer, imported=node_name))
    nodes = tuple(
        sorted(
            DependencyNode(name=node_name, path=path_by_node.get(node_name))
            for node_name in node_names
        )
    )
    return DependencyGraph(nodes=nodes, edges=tuple(sorted(edges)))


def _extract_json_object_text(text: str) -> str:
    json_start = text.find("{")
    json_end = text.rfind("}")
    if json_start < 0 or json_end < json_start:
        raise ValueError("Backend output did not contain a JSON object.")
    return text[json_start : json_end + 1]


def _read_optional_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _read_string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list) is False:
        return ()
    items = cast(list[object], value)
    return tuple(item for item in items if isinstance(item, str))
