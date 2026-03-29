import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.scripts.python.graph.visualize import cli_graph_app, cli_graph_search


runner = CliRunner()


class StubConsole:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def print(self, value: object) -> None:
        self.calls.append(value)


def _write_graph(graph_path: Path) -> None:
    graph_payload: dict[str, object] = {
        "root": {
            "kind": "root",
            "name": "mcfg",
            "source": {"file": "src/machineconfig/scripts/python/mcfg_entry.py"},
            "children": [
                {
                    "kind": "group",
                    "name": "devops",
                    "help": "DevOps operations",
                    "app": {"help": "DevOps operations"},
                    "source": {"file": "src/machineconfig/scripts/python/devops.py"},
                    "children": [
                        {
                            "kind": "group",
                            "name": "self",
                            "help": "Self management",
                            "app": {"help": "Self management"},
                            "source": {"file": "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py"},
                            "children": [
                                {
                                    "kind": "command",
                                    "name": "status",
                                    "short_help": "Status output",
                                    "source": {"file": "src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py"},
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    }
    graph_path.write_text(json.dumps(graph_payload), encoding="utf-8")


def test_search_help_exposes_show_json_option() -> None:
    result = runner.invoke(cli_graph_app.get_app(), ["search", "--help"])

    assert result.exit_code == 0
    assert "--show-json" in result.output


def test_load_search_entries_includes_groups_and_rootless_commands(tmp_path: Path) -> None:
    graph_path = tmp_path.joinpath("cli_graph.json")
    _write_graph(graph_path=graph_path)

    entries = cli_graph_search.load_search_entries(graph_path=graph_path)

    assert [entry.command for entry in entries] == ["devops", "devops self", "devops self status"]


def test_search_cli_graph_runs_help_for_selected_entry_by_default(tmp_path: Path) -> None:
    graph_path = tmp_path.joinpath("cli_graph.json")
    _write_graph(graph_path=graph_path)
    console = StubConsole()
    completed_process = subprocess.CompletedProcess(args=["devops", "self", "--help"], returncode=0)

    with (
        patch.object(cli_graph_search, "install_if_missing"),
        patch.object(
            cli_graph_search,
            "choose_from_dict_with_preview",
            return_value="devops self    [src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py]",
        ),
        patch.object(cli_graph_search, "_console", return_value=console),
        patch.object(cli_graph_search.subprocess, "run", return_value=completed_process) as subprocess_run,
    ):
        return_code = cli_graph_search.search_cli_graph(graph_path=graph_path, show_json=False)

    assert return_code == 0
    subprocess_run.assert_called_once_with(["devops", "self", "--help"], check=False)
    assert len(console.calls) == 1


def test_search_cli_graph_can_show_json_instead_of_running_help(tmp_path: Path) -> None:
    graph_path = tmp_path.joinpath("cli_graph.json")
    _write_graph(graph_path=graph_path)
    console = StubConsole()

    with (
        patch.object(cli_graph_search, "install_if_missing"),
        patch.object(
            cli_graph_search,
            "choose_from_dict_with_preview",
            return_value="devops self    [src/machineconfig/scripts/python/helpers/helpers_devops/cli_self.py]",
        ),
        patch.object(cli_graph_search, "_console", return_value=console),
        patch.object(cli_graph_search.subprocess, "run") as subprocess_run,
    ):
        return_code = cli_graph_search.search_cli_graph(graph_path=graph_path, show_json=True)

    assert return_code == 0
    subprocess_run.assert_not_called()
    assert len(console.calls) == 2
