from dataclasses import dataclass
import json
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import machineconfig.scripts.python.graph.visualize.cli_graph_search as target


type JsonObject = dict[str, object]


@dataclass
class FakeConsole:
    rendered: list[object]

    def print(self, value: object) -> None:
        self.rendered.append(value)


@dataclass(frozen=True)
class CompletedProcessResult:
    returncode: int


def _graph_payload() -> JsonObject:
    return {
        "root": {
            "kind": "root",
            "name": "mcfg",
            "children": [
                {
                    "kind": "group",
                    "name": "graph",
                    "shortPath": "g",
                    "help": "Graph tools",
                    "source": {"file": "src/a_graph.py"},
                    "children": [
                        {
                            "kind": "command",
                            "name": "search",
                            "shortPath": "g s",
                            "short_help": "Search graph",
                            "source": {"file": "src/b_search.py"},
                        }
                    ],
                },
                {
                    "kind": "command",
                    "name": "fire",
                    "short_help": "Run jobs",
                    "source": {"file": "src/c_fire.py"},
                },
            ],
        }
    }


def _write_graph(tmp_path: Path) -> Path:
    graph_path = tmp_path / "cli_graph.json"
    graph_path.write_text(json.dumps(_graph_payload()), encoding="utf-8")
    return graph_path


def test_load_search_entries_normalizes_root_and_short_paths(
    tmp_path: Path,
) -> None:
    entries = target.load_search_entries(graph_path=_write_graph(tmp_path))

    assert [entry.command for entry in entries] == ["graph", "graph search", "fire"]
    assert [entry.source_file for entry in entries] == [
        "src/a_graph.py",
        "src/b_search.py",
        "src/c_fire.py",
    ]
    assert entries[0].short_command == "g"
    assert entries[1].short_command == "g s"
    assert entries[1].help_command == "graph search --help"


def test_search_cli_graph_show_json_prints_summary_and_entry(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = FakeConsole(rendered=[])

    def install_if_missing(
        *,
        which: str,
        binary_name: str | None,
        verbose: bool,
    ) -> None:
        _ = (which, binary_name, verbose)

    def choose_from_dict_with_preview(
        *,
        options_to_preview_mapping: dict[str, str],
        extension: str,
        multi: bool,
        preview_size_percent: int,
    ) -> str | None:
        _ = (extension, multi, preview_size_percent)
        return next(iter(options_to_preview_mapping))

    def run(args: list[str], check: bool) -> CompletedProcessResult:
        _ = (args, check)
        raise AssertionError("subprocess.run should not be used when show_json=True")

    monkeypatch.setattr(target, "install_if_missing", install_if_missing)
    monkeypatch.setattr(
        target,
        "choose_from_dict_with_preview",
        choose_from_dict_with_preview,
    )
    monkeypatch.setattr(target, "_console", lambda: console)
    monkeypatch.setattr(target.subprocess, "run", run)

    return_code = target.search_cli_graph(
        graph_path=_write_graph(tmp_path),
        show_json=True,
    )

    assert return_code == 0
    assert len(console.rendered) == 2


def test_search_cli_graph_runs_selected_help_command(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = FakeConsole(rendered=[])
    seen_commands: list[list[str]] = []

    def install_if_missing(
        *,
        which: str,
        binary_name: str | None,
        verbose: bool,
    ) -> None:
        _ = (which, binary_name, verbose)

    def choose_from_dict_with_preview(
        *,
        options_to_preview_mapping: dict[str, str],
        extension: str,
        multi: bool,
        preview_size_percent: int,
    ) -> str | None:
        _ = (extension, multi, preview_size_percent)
        return next(iter(options_to_preview_mapping))

    def run(args: list[str], check: bool) -> CompletedProcessResult:
        seen_commands.append(args)
        assert check is False
        return CompletedProcessResult(returncode=7)

    monkeypatch.setattr(target, "install_if_missing", install_if_missing)
    monkeypatch.setattr(
        target,
        "choose_from_dict_with_preview",
        choose_from_dict_with_preview,
    )
    monkeypatch.setattr(target, "_console", lambda: console)
    monkeypatch.setattr(target.subprocess, "run", run)

    return_code = target.search_cli_graph(
        graph_path=_write_graph(tmp_path),
        show_json=False,
    )

    assert return_code == 7
    assert seen_commands == [["graph", "--help"]]
    assert len(console.rendered) == 1
