from collections.abc import Iterator

from stackops.scripts.python.graph.python_api_graph import build_python_api_graph, collect_api_module_selections


def test_collect_api_module_selections_uses_docs_api_allowlist() -> None:
    selections = collect_api_module_selections()

    assert "stackops.utils.code" in selections
    assert selections["stackops.utils.code"].include_all
    assert "stackops.scripts.python.devops" not in selections
    assert len(selections) >= 50


def test_python_api_graph_includes_public_members_and_skips_cli_wiring() -> None:
    payload = build_python_api_graph()
    qualified_names = {str(node["qualified_name"]) for node in _walk(payload["root"]) if "qualified_name" in node}

    assert "stackops.utils.code.run_shell_script" in qualified_names
    assert "stackops.utils.installer_utils.installer_cli.install_if_missing" in qualified_names
    assert "stackops.jobs.installer.checks.security_cli.get_app" not in qualified_names
    assert "stackops.jobs.installer.checks.security_cli.main" not in qualified_names


def _walk(node: dict[str, object]) -> Iterator[dict[str, object]]:
    yield node
    children = node.get("children")
    if not isinstance(children, list):
        return
    for child in children:
        if isinstance(child, dict):
            yield from _walk(child)
