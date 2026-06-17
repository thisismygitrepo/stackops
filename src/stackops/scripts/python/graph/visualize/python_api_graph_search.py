import json
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from stackops.utils.installer_utils.installer_cli import install_if_missing
from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview


type JsonObject = dict[str, object]


@dataclass(frozen=True)
class PythonApiGraphSearchEntry:
    qualified_name: str
    source_file: str
    kind: str
    entry: JsonObject


def load_search_entries(graph_path: Path) -> list[PythonApiGraphSearchEntry]:
    graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    graph_root = _as_json_object(graph_data.get("root") if isinstance(graph_data, dict) else None)
    if graph_root is None:
        raise ValueError(f"Invalid graph root in {graph_path}")

    entries: list[PythonApiGraphSearchEntry] = []

    def walk(node: JsonObject) -> None:
        kind = _as_string(node.get("kind"))
        qualified_name = _as_string(node.get("qualified_name"))
        source = _as_json_object(node.get("source"))
        source_file = _as_string(source.get("file")) if source is not None else ""

        if kind != "root" and qualified_name:
            entries.append(PythonApiGraphSearchEntry(qualified_name=qualified_name, source_file=source_file, kind=kind, entry=node))

        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                child_node = _as_json_object(child)
                if child_node is not None:
                    walk(child_node)

    walk(graph_root)
    entries.sort(key=lambda entry: (entry.source_file, entry.qualified_name))
    return entries


def search_python_api_graph(graph_path: Path, json_output: bool) -> int:
    install_if_missing(which="tv", binary_name=None, verbose=True)
    entries = load_search_entries(graph_path=graph_path)
    if not entries:
        raise ValueError(f"No searchable Python API entries found in {graph_path}")

    options_to_preview_mapping, entry_lookup = _build_entry_lookup(entries=entries)
    selected_key = choose_from_dict_with_preview(
        options_to_preview_mapping=options_to_preview_mapping,
        extension="md",
        multi=False,
        preview_size_percent=70,
    )
    if selected_key is None:
        return 0

    selected_entry = entry_lookup[selected_key]
    console = Console()
    if json_output:
        console.print(Panel(_result_summary(entry=selected_entry, json_output=json_output), title="Python API Search Result", border_style="green"))
        console.print(
            Panel(
                Syntax(json.dumps(selected_entry.entry, ensure_ascii=False, indent=2), "json", line_numbers=True),
                title="Full Python API Graph Entry",
                border_style="cyan",
            )
        )
        return 0

    console.print(Panel(Markdown(_entry_summary_markdown(entry=selected_entry)), title="Python API Summary", border_style="green"))
    return 0


def _build_entry_lookup(entries: list[PythonApiGraphSearchEntry]) -> tuple[dict[str, str], dict[str, PythonApiGraphSearchEntry]]:
    options_to_preview_mapping: dict[str, str] = {}
    entry_lookup: dict[str, PythonApiGraphSearchEntry] = {}

    for entry in entries:
        option_key = f"{entry.qualified_name}    [{entry.kind}]    [{entry.source_file or '-'}]"
        entry_lookup[option_key] = entry
        options_to_preview_mapping[option_key] = _entry_summary_markdown(entry=entry)

    return options_to_preview_mapping, entry_lookup


def _result_summary(entry: PythonApiGraphSearchEntry, json_output: bool) -> str:
    lines = [
        f"[bold]Import path:[/bold] {entry.qualified_name}",
        f"[bold]Kind:[/bold] {entry.kind}",
        f"[bold]Source file:[/bold] {entry.source_file or '-'}",
        f"[bold]Action:[/bold] {'show json' if json_output else 'show summary'}",
    ]
    return "\n".join(lines)


def _entry_summary_markdown(entry: PythonApiGraphSearchEntry) -> str:
    node = entry.entry
    lines = [f"# `{entry.qualified_name}`", "", f"**Kind:** `{entry.kind}`"]

    source = _as_json_object(node.get("source"))
    if source is not None:
        lines.extend(["", "## Source", ""])
        for label, value in (
            ("File", _as_string(source.get("file"))),
            ("Module", _as_string(source.get("module"))),
            ("Object", _as_string(source.get("object"))),
            ("Line", str(source.get("line")) if source.get("line") is not None else ""),
        ):
            if value:
                lines.append(f"- **{label}:** `{value}`")
        docs_pages = _as_string_list(source.get("docs_pages"))
        if docs_pages:
            lines.append(f"- **Docs:** {', '.join(f'`{page}`' for page in docs_pages)}")

    signature = _signature_text(node)
    if signature:
        lines.extend(["", "## Signature", "", "```python", signature, "```"])

    description_blocks = _description_blocks(node)
    if description_blocks:
        lines.extend(["", "## Description", ""])
        for block in description_blocks:
            lines.extend([_markdown_text(block), ""])
        lines.pop()

    child_rows = _child_rows(node)
    if child_rows:
        lines.extend(["", "## Children", "", _child_table(rows=child_rows)])

    return "\n".join(lines).rstrip() + "\n"


def _signature_text(node: JsonObject) -> str:
    signature = _as_json_object(node.get("signature"))
    if signature is None:
        return ""
    return _as_string(signature.get("text"))


def _description_blocks(node: JsonObject) -> list[str]:
    values = [_as_string(node.get("help")), _as_string(node.get("doc"))]
    blocks: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_multiline(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        blocks.append(cleaned)
    return blocks


def _child_rows(node: JsonObject) -> list[tuple[str, str, str]]:
    children = node.get("children")
    if not isinstance(children, list):
        return []

    rows: list[tuple[str, str, str]] = []
    for child in children[:30]:
        child_node = _as_json_object(child)
        if child_node is None:
            continue
        rows.append(
            (
                _as_string(child_node.get("qualified_name")) or _as_string(child_node.get("name")) or "-",
                _as_string(child_node.get("kind")) or "-",
                _compact_whitespace(_as_string(child_node.get("help"))) or "-",
            )
        )
    if len(children) > 30:
        rows.append((f"... {len(children) - 30} more", "-", "-"))
    return rows


def _child_table(rows: list[tuple[str, str, str]]) -> str:
    lines = ["| Import path | Kind | Summary |", "|---|---|---|"]
    for qualified_name, kind, summary in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{qualified_name}`" if qualified_name != "-" else "-",
                    _markdown_table_cell(kind),
                    _markdown_table_cell(summary),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _clean_multiline(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines()).strip()


def _compact_whitespace(value: str) -> str:
    return " ".join(value.split())


def _markdown_text(value: str) -> str:
    return value.replace("<", "\\<").replace(">", "\\>")


def _markdown_table_cell(value: str) -> str:
    return _markdown_text(value).replace("|", "\\|").replace("\n", "<br>")


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(key, str) for key in value):
        return None
    return value


def _as_string(value: object) -> str:
    return value if isinstance(value, str) else ""
