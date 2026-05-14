import json
import subprocess
from pathlib import Path

import pytest

from stackops.scripts.python.graph.visualize import cli_graph_search


def _fake_install_if_missing(*, which: str, binary_name: str | None, verbose: bool) -> None:
    _ = which, binary_name, verbose


def test_help_command_includes_stackops_root() -> None:
    entry = cli_graph_search.CliGraphSearchEntry(
        source_file="src/stackops/scripts/python/graph/visualize/cli_graph_app.py",
        command_tokens=("devops", "self", "explore", "search"),
        short_command_tokens=("d", "s", "x", "s"),
        entry={},
    )

    assert entry.command == "devops self explore search"
    assert entry.help_command == "stackops devops self explore search --help"


def test_search_cli_graph_executes_root_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_path = tmp_path.joinpath("cli_graph.json")
    graph_path.write_text(
        json.dumps(
            {
                "root": {
                    "kind": "root",
                    "name": "stackops",
                    "children": [
                        {
                            "kind": "group",
                            "name": "devops",
                            "source": {"file": "src/stackops/scripts/python/devops.py"},
                            "children": [
                                {
                                    "kind": "group",
                                    "name": "self",
                                    "source": {"file": "src/stackops/scripts/python/helpers/helpers_devops/cli_self.py"},
                                    "children": [
                                        {
                                            "kind": "group",
                                            "name": "explore",
                                            "source": {
                                                "file": "src/stackops/scripts/python/helpers/helpers_devops/cli_self.py"
                                            },
                                            "children": [
                                                {
                                                    "kind": "command",
                                                    "name": "search",
                                                    "source": {
                                                        "file": "src/stackops/scripts/python/graph/visualize/cli_graph_app.py"
                                                    },
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    captured_commands: list[list[str]] = []

    def fake_choose_from_dict_with_preview(
        *,
        options_to_preview_mapping: dict[str, str],
        extension: str,
        multi: bool,
        preview_size_percent: float,
    ) -> str:
        assert extension == "json"
        assert multi is False
        assert preview_size_percent == 70
        assert len(options_to_preview_mapping) == 3
        selected_key = "devops self explore search    [src/stackops/scripts/python/graph/visualize/cli_graph_app.py]"
        assert selected_key in options_to_preview_mapping
        assert "Help target: stackops devops self explore search --help" in options_to_preview_mapping[selected_key]
        return selected_key

    def fake_run(args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        captured_commands.append(args)
        assert check is False
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr("stackops.utils.installer_utils.installer_cli.install_if_missing", _fake_install_if_missing)
    monkeypatch.setattr("stackops.utils.options_utils.tv_options.choose_from_dict_with_preview", fake_choose_from_dict_with_preview)
    monkeypatch.setattr("subprocess.run", fake_run)

    return_code = cli_graph_search.search_cli_graph(graph_path=graph_path, show_json=False)

    assert return_code == 0
    assert captured_commands == [["stackops", "devops", "self", "explore", "search", "--help"]]
