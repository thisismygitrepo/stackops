import json
from dataclasses import dataclass
from pathlib import Path
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from machineconfig.utils.installer_utils.installer_cli import install_if_missing
from machineconfig.utils.options_utils.tv_options import choose_from_dict_with_preview


type JsonObject = dict[str, object]


@dataclass(frozen=True)
class CliGraphSearchEntry:
    source_file: str
    command_tokens: tuple[str, ...]
    entry: JsonObject

    @property
    def command(self) -> str:
        return " ".join(self.command_tokens)

    @property
    def help_command(self) -> str:
        return f"{self.command} --help"


def load_search_entries(graph_path: Path) -> list[CliGraphSearchEntry]:
    graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    graph_root = _as_json_object(graph_data.get("root") if isinstance(graph_data, dict) else None)
    if graph_root is None:
        raise ValueError(f"Invalid graph root in {graph_path}")

    entries: list[CliGraphSearchEntry] = []

    def walk(node: JsonObject, parent_tokens: list[str]) -> None:
        node_name = _as_string(node.get("name"))
        node_tokens = [*parent_tokens, *([node_name] if node_name else [])]
        node_kind = _as_string(node.get("kind"))
        source = _as_json_object(node.get("source"))
        source_file = _as_string(source.get("file")) if source is not None else ""
        command_tokens = _normalize_command_tokens(tokens=node_tokens)

        if node_kind in {"group", "command"} and source_file.endswith(".py") and command_tokens:
            entries.append(
                CliGraphSearchEntry(
                    source_file=source_file,
                    command_tokens=command_tokens,
                    entry=node,
                )
            )

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                child_node = _as_json_object(child)
                if child_node is not None:
                    walk(node=child_node, parent_tokens=node_tokens)

    walk(node=graph_root, parent_tokens=[])
    entries.sort(key=lambda entry: (entry.source_file, entry.command))
    return entries


def search_cli_graph(graph_path: Path, show_json: bool) -> int:
    install_if_missing(which="tv", binary_name=None, verbose=True)
    entries = load_search_entries(graph_path=graph_path)
    if not entries:
        raise ValueError(f"No searchable CLI entries found in {graph_path}")

    options_to_preview_mapping, entry_lookup = _build_entry_lookup(entries=entries)
    selected_key = choose_from_dict_with_preview(
        options_to_preview_mapping=options_to_preview_mapping,
        extension="json",
        multi=False,
        preview_size_percent=70,
    )
    if selected_key is None:
        return 0

    selected_entry = entry_lookup[selected_key]
    console = _console()
    console.print(
        Panel(
            f"[bold]Source file:[/bold] {selected_entry.source_file}\n"
            f"[bold]Command:[/bold] {selected_entry.command}\n"
            f"[bold]Action:[/bold] {selected_entry.help_command if not show_json else 'show json'}",
            title="🔎 CLI Graph Search Result",
            border_style="green",
        )
    )

    if show_json:
        console.print(
            Panel(
                Syntax(json.dumps(selected_entry.entry, ensure_ascii=False, indent=2), "json", line_numbers=True),
                title="📦 Full cli_graph.json Entry",
                border_style="cyan",
            )
        )
        return 0

    completed_process = subprocess.run([*selected_entry.command_tokens, "--help"], check=False)
    return completed_process.returncode


def _build_entry_lookup(entries: list[CliGraphSearchEntry]) -> tuple[dict[str, str], dict[str, CliGraphSearchEntry]]:
    options_to_preview_mapping: dict[str, str] = {}
    entry_lookup: dict[str, CliGraphSearchEntry] = {}

    for entry in entries:
        option_key = f"{entry.command}    [{entry.source_file}]"
        entry_lookup[option_key] = entry
        summary = _node_summary(node=entry.entry)
        header = f"Source: {entry.source_file}\nCommand: {entry.command}\n"
        if summary:
            options_to_preview_mapping[option_key] = (
                f"{header}Help target: {entry.help_command}\nSummary: {summary}\n\n"
                + json.dumps(entry.entry, ensure_ascii=False, indent=2)
            )
        else:
            options_to_preview_mapping[option_key] = (
                f"{header}Help target: {entry.help_command}\n\n"
                + json.dumps(entry.entry, ensure_ascii=False, indent=2)
            )

    return options_to_preview_mapping, entry_lookup


def _node_summary(node: JsonObject) -> str:
    node_kind = _as_string(node.get("kind"))
    if node_kind == "group":
        app = _as_json_object(node.get("app"))
        return (
            _as_string(app.get("help")) if app is not None else ""
        ) or _as_string(node.get("help")) or _as_string(node.get("doc")) or _as_string(node.get("name"))
    return (
        _as_string(node.get("short_help"))
        or _as_string(node.get("help"))
        or _as_string(node.get("doc"))
        or _as_string(node.get("name"))
    )


def _normalize_command_tokens(tokens: list[str]) -> tuple[str, ...]:
    if tokens and tokens[0] == "mcfg":
        normalized_tokens = tokens[1:]
    else:
        normalized_tokens = tokens
    return tuple(token for token in normalized_tokens if token)


def _as_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(key, str) for key in value):
        return None
    return value


def _as_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _console() -> Console:
    return Console()
