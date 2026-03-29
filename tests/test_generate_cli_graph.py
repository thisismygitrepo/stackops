from collections.abc import Iterator

from machineconfig.scripts.python.graph.generate_cli_graph import build_cli_graph


type JsonObject = dict[str, object]


def _as_json_object(value: object) -> JsonObject:
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return value


def _as_string(value: object) -> str:
    assert isinstance(value, str)
    return value


def _find_child_by_name(node: JsonObject, name: str) -> JsonObject:
    children = node.get("children")
    assert isinstance(children, list)
    for child in children:
        child_node = _as_json_object(value=child)
        if child_node.get("name") == name:
            return child_node
    raise AssertionError(f"Could not find child node {name!r}")


def _walk_nodes(node: JsonObject) -> Iterator[JsonObject]:
    yield node
    children = node.get("children")
    if not isinstance(children, list):
        return
    for child in children:
        child_node = _as_json_object(value=child)
        yield from _walk_nodes(node=child_node)


def test_build_cli_graph_includes_root_relative_full_and_short_paths() -> None:
    graph = build_cli_graph()
    root = _as_json_object(value=graph["root"])
    devops = _find_child_by_name(node=root, name="devops")
    install = _find_child_by_name(node=devops, name="install")

    assert root["fullPath"] == ""
    assert root["shortPath"] == ""
    assert devops["fullPath"] == "devops"
    assert devops["shortPath"] == "d"
    assert install["fullPath"] == "devops install"
    assert install["shortPath"] == "d i"


def test_build_cli_graph_populates_paths_for_every_node() -> None:
    graph = build_cli_graph()
    root = _as_json_object(value=graph["root"])

    for node in _walk_nodes(node=root):
        assert isinstance(node.get("fullPath"), str)
        assert isinstance(node.get("shortPath"), str)

        node_kind = _as_string(value=node["kind"])
        if node_kind == "root":
            continue

        full_path = _as_string(value=node["fullPath"])
        short_path = _as_string(value=node["shortPath"])
        name = _as_string(value=node["name"])

        assert full_path
        assert short_path
        assert full_path.split(" ")[-1] == name
        assert len(full_path.split(" ")) == len(short_path.split(" "))
