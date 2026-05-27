from stackops.scripts.python.graph.cli_graph_tree import build_cli_graph


def _child_by_name(node: dict, name: str) -> dict:
    for child in node.get("children", []):
        if child.get("name") == name:
            return child
    raise AssertionError(f"Missing child node: {name}")


def test_stackops_entry_lazy_dispatchers_resolve_to_groups() -> None:
    graph = build_cli_graph()
    root = graph["root"]

    for command_name in ("devops", "cloud", "terminal", "agents", "utils", "seek"):
        node = _child_by_name(root, command_name)

        assert node["kind"] == "group"
        assert node["children"]
        assert node["source"]["dispatches_to"].endswith(f".{command_name}.get_app")

    agents = _child_by_name(root, "agents")
    assert _child_by_name(agents, "browser")["kind"] == "group"
    assert _child_by_name(agents, "add-skill")["kind"] == "command"
