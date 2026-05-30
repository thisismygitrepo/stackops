import json
from io import StringIO
from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from stackops.scripts.python.graph.visualize import cli_graph_search
from stackops.scripts.python.graph.visualize.cli_graph_typer_app import build_cli_graph_app


def test_search_cli_graph_default_renders_markdown_summary(monkeypatch, tmp_path: Path) -> None:
    graph_path = _write_graph(tmp_path=tmp_path)
    selected_keys: list[str] = []
    preview_extensions: list[str | None] = []

    def choose_first(options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> str:
        assert multi is False
        assert preview_size_percent == 70
        preview_extensions.append(extension)
        selected_key = next(iter(options_to_preview_mapping))
        selected_keys.append(selected_key)
        assert "## Options" in options_to_preview_mapping[selected_key]
        return selected_key

    stream = StringIO()
    monkeypatch.setattr(cli_graph_search, "install_if_missing", lambda **_kwargs: None)
    monkeypatch.setattr(cli_graph_search, "choose_from_dict_with_preview", choose_first)
    monkeypatch.setattr(cli_graph_search, "_console", lambda: Console(file=stream, force_terminal=False, width=120))

    return_code = cli_graph_search.search_cli_graph(graph_path=graph_path, json_output=False)

    assert return_code == 0
    assert preview_extensions == ["md"]
    assert selected_keys == ["foo    [src/example.py]"]
    output = stream.getvalue()
    assert "CLI Command Summary" in output
    assert "stackops foo" in output
    assert "Run foo." in output
    assert "--json" in output
    assert "Full cli_graph.json Entry" not in output


def test_search_cli_graph_json_option_prints_raw_entry(monkeypatch, tmp_path: Path) -> None:
    graph_path = _write_graph(tmp_path=tmp_path)

    def choose_first(options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> str:
        return next(iter(options_to_preview_mapping))

    stream = StringIO()
    monkeypatch.setattr(cli_graph_search, "install_if_missing", lambda **_kwargs: None)
    monkeypatch.setattr(cli_graph_search, "choose_from_dict_with_preview", choose_first)
    monkeypatch.setattr(cli_graph_search, "_console", lambda: Console(file=stream, force_terminal=False, width=120))

    return_code = cli_graph_search.search_cli_graph(graph_path=graph_path, json_output=True)

    assert return_code == 0
    output = stream.getvalue()
    assert "Full cli_graph.json Entry" in output
    assert '"name": "foo"' in output
    assert "CLI Command Summary" not in output


def test_search_help_uses_json_option_alias() -> None:
    result = CliRunner().invoke(build_cli_graph_app(), ["search", "--help"])

    assert result.exit_code == 0
    assert "--json" in result.output
    assert "-j" in result.output
    assert "--show-json" not in result.output


def _write_graph(tmp_path: Path) -> Path:
    graph_path = tmp_path / "cli_graph.json"
    graph_path.write_text(json.dumps(_graph_payload()), encoding="utf-8")
    return graph_path


def _graph_payload() -> dict[str, object]:
    return {
        "root": {
            "kind": "root",
            "name": "stackops",
            "children": [
                {
                    "kind": "command",
                    "name": "foo",
                    "fullPath": "stackops foo",
                    "shortPath": "f",
                    "help": "Run foo.",
                    "doc": "Run foo with a target.",
                    "source": {"file": "src/example.py", "module": "example", "callable": "foo"},
                    "aliases": [{"name": "f", "hidden": True, "help": "Run foo."}],
                    "signature": {
                        "name": "foo",
                        "parameters": [
                            {
                                "name": "target",
                                "kind": "positional_or_keyword",
                                "type": "str",
                                "default": None,
                                "required": True,
                                "typer": {"kind": "argument", "help": "Target to process."},
                            },
                            {
                                "name": "json_output",
                                "kind": "positional_or_keyword",
                                "type": "bool",
                                "default": False,
                                "required": False,
                                "typer": {"kind": "option", "param_decls": ["--json", "-j"], "help": "Print JSON."},
                            },
                        ],
                    },
                }
            ],
        }
    }
