import pytest

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import DEFAULT_SEAPRATOR
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_logic import build_logic_context_from_graph


def test_build_logic_context_from_graph_uses_leaf_commands_only() -> None:
    graph_payload: dict[str, object] = {
        "root": {
            "name": "stackops",
            "children": [
                {
                    "kind": "group",
                    "name": "devops",
                    "fullPath": "devops",
                    "source": {"file": "src/stackops/scripts/python/devops.py"},
                    "children": [
                        {
                            "kind": "command",
                            "name": "install",
                            "fullPath": "devops install",
                            "source": {"file": "src/stackops/scripts/python/devops.py"},
                        }
                    ],
                },
                {
                    "kind": "command",
                    "name": "status",
                    "fullPath": "status",
                    "source": {"file": "src/stackops/scripts/python/status.py"},
                },
            ],
        }
    }

    assert build_logic_context_from_graph(graph_payload=graph_payload) == DEFAULT_SEAPRATOR.join(
        [
            "file: src/stackops/scripts/python/devops.py\ncommand: devops install",
            "file: src/stackops/scripts/python/status.py\ncommand: status",
        ]
    )


def test_build_logic_context_from_graph_rejects_missing_command_metadata() -> None:
    graph_payload: dict[str, object] = {
        "root": {
            "children": [
                {
                    "kind": "command",
                    "name": "status",
                    "fullPath": "status",
                    "source": {},
                }
            ]
        }
    }

    with pytest.raises(ValueError, match="source\\.file and fullPath"):
        build_logic_context_from_graph(graph_payload=graph_payload)