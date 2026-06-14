from datetime import date

from typer.testing import CliRunner

from stackops.scripts.python.graph.cli_graph_apps import load_app_model
from stackops.scripts.python.graph.cli_graph_nodes import build_children
from stackops.scripts.python.graph.cli_graph_shared import AppRef
from stackops.scripts.python.helpers.helpers_devops import cli_self_assets, stackops_skill_refs


SAMPLE_GRAPH = {
    "root": {
        "kind": "root",
        "name": "stackops",
        "source": {"file": "src/stackops/scripts/python/stackops_entry.py"},
        "children": [
            {
                "kind": "group",
                "name": "devops",
                "fullPath": "devops",
                "source": {
                    "file": "src/stackops/scripts/python/stackops_entry.py",
                    "dispatches_to": "stackops.scripts.python.devops.get_app",
                },
                "aliases": [{"name": "d", "hidden": True}],
                "children": [
                    {
                        "kind": "command",
                        "name": "install",
                        "fullPath": "devops install",
                        "source": {"file": "src/stackops/scripts/python/devops.py", "callable": "install"},
                    }
                ],
            },
            {
                "kind": "group",
                "name": "type-fix",
                "fullPath": "utils pyproject type-fix",
                "source": {
                    "file": "src/stackops/scripts/python/helpers/helpers_utils/pyproject_utils_app.py",
                    "dispatches_to": "stackops.scripts.python.helpers.helpers_utils.type_fix.get_app",
                },
                "children": [],
            },
        ],
    }
}


def test_cli_map_uses_canonical_tree_without_alias_nodes() -> None:
    rendered = stackops_skill_refs.render_cli_map(
        cli_graph_payload=SAMPLE_GRAPH,
        project_scripts={"devops": "stackops.scripts.python.devops:main"},
        generated_on=date(2026, 6, 9),
    )

    assert "Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-09." in rendered
    assert "- `devops` -> `stackops.scripts.python.devops:main`" in rendered
    assert "├─ devops" in rendered
    assert "│  └─ install" in rendered
    assert "└─ type-fix (callback group)" in rendered
    assert "\n├─ d\n" not in rendered


def test_source_map_links_groups_and_leaf_commands() -> None:
    rendered = stackops_skill_refs.render_source_map(cli_graph_payload=SAMPLE_GRAPH, generated_on=date(2026, 6, 9))

    assert "- `devops` -> `src/stackops/scripts/python/stackops_entry.py` -> `stackops.scripts.python.devops.get_app` via `devops`" in rendered
    assert "- `devops install` -> `src/stackops/scripts/python/devops.py` -> `install`" in rendered
    assert "devops self build-assets update-skill-refs" in rendered


def test_update_skill_refs_command_is_registered() -> None:
    result = CliRunner().invoke(cli_self_assets.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "update-skill-refs" in result.stdout


def test_cli_graph_expands_static_loop_command_registrations() -> None:
    app_model = load_app_model(
        AppRef(
            module="stackops.scripts.python.helpers.helpers_devops.cli_config_tmux",
            factory="get_app",
        )
    )

    children = build_children(
        app_model=app_model,
        parent_full_tokens=("devops", "config", "terminal", "tmux-style"),
        parent_short_tokens=("d", "c", "t", "s"),
    )
    child_names = {child["name"] for child in children}

    assert {
        "install-oh-my-tmux",
        "apply-stackops-local",
        "preset",
        "set-option",
        "reload",
        "status",
    } <= child_names
