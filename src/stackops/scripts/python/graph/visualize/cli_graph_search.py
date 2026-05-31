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
class CliGraphSearchEntry:
    source_file: str
    command_tokens: tuple[str, ...]
    short_command_tokens: tuple[str, ...]
    entry: JsonObject

    @property
    def command(self) -> str:
        return " ".join(self.command_tokens)

    @property
    def short_command(self) -> str:
        return " ".join(self.short_command_tokens)

    @property
    def executable_command_tokens(self) -> tuple[str, ...]:
        return ("stackops", *self.command_tokens)

    @property
    def executable_command(self) -> str:
        return " ".join(self.executable_command_tokens)

    @property
    def help_command(self) -> str:
        return f"{self.executable_command} --help"


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
        short_command_tokens = _short_command_tokens(node=node, fallback_tokens=command_tokens)

        if node_kind in {"group", "command"} and source_file.endswith(".py") and command_tokens:
            entries.append(
                CliGraphSearchEntry(source_file=source_file, command_tokens=command_tokens, short_command_tokens=short_command_tokens, entry=node)
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


def search_cli_graph(graph_path: Path, json_output: bool) -> int:
    install_if_missing(which="tv", binary_name=None, verbose=True)
    entries = load_search_entries(graph_path=graph_path)
    if not entries:
        raise ValueError(f"No searchable CLI entries found in {graph_path}")

    options_to_preview_mapping, entry_lookup = _build_entry_lookup(entries=entries)
    selected_key = choose_from_dict_with_preview(
        options_to_preview_mapping=options_to_preview_mapping, extension="md", multi=False, preview_size_percent=70
    )
    if selected_key is None:
        return 0

    selected_entry = entry_lookup[selected_key]
    console = _console()
    if json_output:
        console.print(
            Panel(_search_result_summary(entry=selected_entry, json_output=json_output), title="🔎 CLI Graph Search Result", border_style="green")
        )
        console.print(
            Panel(
                Syntax(json.dumps(selected_entry.entry, ensure_ascii=False, indent=2), "json", line_numbers=True),
                title="📦 Full cli_graph.json Entry",
                border_style="cyan",
            )
        )
        return 0

    console.print(Panel(Markdown(_command_summary_markdown(entry=selected_entry)), title="CLI Command Summary", border_style="green"))
    return 0


def _build_entry_lookup(entries: list[CliGraphSearchEntry]) -> tuple[dict[str, str], dict[str, CliGraphSearchEntry]]:
    options_to_preview_mapping: dict[str, str] = {}
    entry_lookup: dict[str, CliGraphSearchEntry] = {}

    for entry in entries:
        option_key = f"{entry.command}    [{entry.source_file}]"
        entry_lookup[option_key] = entry
        options_to_preview_mapping[option_key] = _command_summary_markdown(entry=entry)

    return options_to_preview_mapping, entry_lookup


def _node_summary(node: JsonObject) -> str:
    node_kind = _as_string(node.get("kind"))
    if node_kind == "group":
        app = _as_json_object(node.get("app"))
        return (
            (_as_string(app.get("help")) if app is not None else "")
            or _as_string(node.get("help"))
            or _as_string(node.get("doc"))
            or _as_string(node.get("name"))
        )
    return _as_string(node.get("short_help")) or _as_string(node.get("help")) or _as_string(node.get("doc")) or _as_string(node.get("name"))


def _normalize_command_tokens(tokens: list[str]) -> tuple[str, ...]:
    if tokens and tokens[0] == "stackops":
        normalized_tokens = tokens[1:]
    else:
        normalized_tokens = tokens
    return tuple(token for token in normalized_tokens if token)


def _short_command_tokens(node: JsonObject, fallback_tokens: tuple[str, ...]) -> tuple[str, ...]:
    short_path = _as_string(node.get("shortPath")).strip()
    if not short_path:
        return fallback_tokens
    return tuple(token for token in short_path.split() if token)


def _distinct_short_command(entry: CliGraphSearchEntry) -> str | None:
    if not entry.short_command or entry.short_command == entry.command:
        return None
    return entry.short_command


def preview_header(entry: CliGraphSearchEntry) -> str:
    lines = [f"Source: {entry.source_file}", f"Command: {entry.command}"]
    short_command = _distinct_short_command(entry=entry)
    if short_command is not None:
        lines.append(f"Short command: {short_command}")
    return "\n".join(lines) + "\n"


def _search_result_summary(entry: CliGraphSearchEntry, json_output: bool) -> str:
    lines = [f"[bold]Source file:[/bold] {entry.source_file}", f"[bold]Command:[/bold] {entry.command}"]
    short_command = _distinct_short_command(entry=entry)
    if short_command is not None:
        lines.append(f"[bold]Short command:[/bold] {short_command}")
    lines.append(f"[bold]Action:[/bold] {'show json' if json_output else 'show summary'}")
    return "\n".join(lines)


def _command_summary_markdown(entry: CliGraphSearchEntry) -> str:
    node = entry.entry
    lines = [f"# `{entry.executable_command}`", "", _metadata_line(entry=entry), "", "## Usage", "", "```bash", _usage_line(entry=entry), "```"]

    description_blocks = _description_blocks(node=node)
    if description_blocks:
        lines.extend(["", "## Description", ""])
        for block in description_blocks:
            lines.extend([_escape_markdown_text(block), ""])
        lines.pop()

    aliases = _aliases(node=node)
    if aliases:
        lines.extend(["", "## Aliases", ""])
        for alias in aliases:
            alias_name = _as_string(alias.get("name"))
            alias_help = _as_string(alias.get("help"))
            alias_line = f"- `{alias_name}`"
            if alias_help:
                alias_line += f" - {_escape_markdown_text(_compact_whitespace(alias_help))}"
            lines.append(alias_line)

    parameters = _signature_parameters(node=node)
    argument_rows = [_parameter_row(parameter=parameter) for parameter in parameters if _parameter_typer_kind(parameter=parameter) == "argument"]
    option_rows = [_parameter_row(parameter=parameter) for parameter in parameters if _parameter_typer_kind(parameter=parameter) == "option"]

    if argument_rows:
        lines.extend(["", "## Arguments", "", _parameter_table(rows=argument_rows)])
    if option_rows:
        lines.extend(["", "## Options", "", _parameter_table(rows=option_rows)])

    child_rows = _child_rows(node=node)
    if child_rows:
        lines.extend(["", "## Subcommands", "", _child_table(rows=child_rows)])

    source = _as_json_object(node.get("source"))
    if source is not None:
        lines.extend(["", "## Source", ""])
        for label, value in (
            ("File", _as_string(source.get("file"))),
            ("Module", _as_string(source.get("module"))),
            ("Callable", _as_string(source.get("callable"))),
            ("Dispatches to", _as_string(source.get("dispatches_to"))),
        ):
            if value:
                lines.append(f"- **{label}:** `{value}`")

    return "\n".join(lines).rstrip() + "\n"


def _metadata_line(entry: CliGraphSearchEntry) -> str:
    node_kind = _as_string(entry.entry.get("kind")) or "entry"
    parts = [f"**Kind:** `{node_kind}`"]
    short_command = _distinct_short_command(entry=entry)
    if short_command is not None:
        parts.append(f"**Short command:** `{short_command}`")
    parts.append(f"**Full help:** `{entry.help_command}`")
    return " | ".join(parts)


def _usage_line(entry: CliGraphSearchEntry) -> str:
    node_kind = _as_string(entry.entry.get("kind"))
    if node_kind == "group":
        return f"{entry.executable_command} [COMMAND] [ARGS]..."

    parameters = _signature_parameters(node=entry.entry)
    option_parameters = [parameter for parameter in parameters if _parameter_typer_kind(parameter=parameter) == "option"]
    argument_parameters = [parameter for parameter in parameters if _parameter_typer_kind(parameter=parameter) == "argument"]
    tokens = [entry.executable_command]
    if option_parameters:
        tokens.append("[OPTIONS]")
    for parameter in argument_parameters:
        name = _as_string(parameter.get("name")).replace("_", "-").upper()
        if not name:
            continue
        tokens.append(f"<{name}>" if _as_bool(parameter.get("required")) else f"[{name}]")
    return " ".join(tokens)


def _description_blocks(node: JsonObject) -> list[str]:
    values: list[str] = []
    for key in ("short_help", "help", "doc"):
        values.append(_as_string(node.get(key)))

    app = _as_json_object(node.get("app"))
    if app is not None:
        values.append(_as_string(app.get("help")))

    blocks: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_multiline(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        blocks.append(cleaned)
    return blocks


def _signature_parameters(node: JsonObject) -> list[JsonObject]:
    signature = _as_json_object(node.get("signature"))
    if signature is None:
        return []

    parameters = signature.get("parameters")
    if not isinstance(parameters, list):
        return []

    result: list[JsonObject] = []
    for parameter in parameters:
        parameter_object = _as_json_object(parameter)
        if parameter_object is None:
            continue
        if _as_string(parameter_object.get("name")) == "ctx":
            continue
        if _parameter_typer_kind(parameter=parameter_object) not in {"argument", "option"}:
            continue
        result.append(parameter_object)
    return result


def _parameter_typer_kind(parameter: JsonObject) -> str:
    typer_data = _as_json_object(parameter.get("typer"))
    return _as_string(typer_data.get("kind")) if typer_data is not None else ""


def _parameter_row(parameter: JsonObject) -> tuple[str, str, str, str, str]:
    typer_data = _as_json_object(parameter.get("typer"))
    typer_kind = _parameter_typer_kind(parameter=parameter)
    name = _as_string(parameter.get("name"))
    if typer_kind == "option" and typer_data is not None:
        param_decls = _as_string_list(typer_data.get("param_decls"))
        label = ", ".join(f"`{decl}`" for decl in param_decls) if param_decls else f"`--{name.replace('_', '-')}`"
    else:
        label = f"`{name.replace('_', '-').upper()}`"

    help_text = _as_string(typer_data.get("help")) if typer_data is not None else ""
    return (
        label,
        _as_string(parameter.get("type")) or "-",
        "yes" if _as_bool(parameter.get("required")) else "no",
        _format_default(value=parameter.get("default"), required=_as_bool(parameter.get("required"))),
        _compact_whitespace(help_text) or "-",
    )


def _parameter_table(rows: list[tuple[str, str, str, str, str]]) -> str:
    lines = ["| Parameter | Type | Required | Default | Help |", "|---|---|---:|---|---|"]
    for label, type_name, required, default, help_text in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    _markdown_table_cell(type_name),
                    _markdown_table_cell(required),
                    _markdown_table_cell(default),
                    _markdown_table_cell(help_text),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _child_rows(node: JsonObject) -> list[tuple[str, str, str, str]]:
    children = node.get("children")
    if not isinstance(children, list):
        return []

    rows: list[tuple[str, str, str, str]] = []
    for child in children[:25]:
        child_node = _as_json_object(child)
        if child_node is None:
            continue
        alias_names = ", ".join(_as_string(alias.get("name")) for alias in _aliases(node=child_node) if _as_string(alias.get("name")))
        rows.append(
            (
                _as_string(child_node.get("name")) or "-",
                _as_string(child_node.get("kind")) or "-",
                alias_names or "-",
                _compact_whitespace(_node_summary(node=child_node)) or "-",
            )
        )
    if len(children) > 25:
        rows.append((f"... {len(children) - 25} more", "-", "-", "-"))
    return rows


def _child_table(rows: list[tuple[str, str, str, str]]) -> str:
    lines = ["| Command | Kind | Aliases | Summary |", "|---|---|---|---|"]
    for command, kind, aliases, summary in rows:
        lines.append(
            "| "
            + " | ".join(
                [f"`{command}`" if command != "-" else "-", _markdown_table_cell(kind), _markdown_table_cell(aliases), _markdown_table_cell(summary)]
            )
            + " |"
        )
    return "\n".join(lines)


def _aliases(node: JsonObject) -> list[JsonObject]:
    aliases = node.get("aliases")
    if not isinstance(aliases, list):
        return []
    return [alias for alias in (_as_json_object(alias) for alias in aliases) if alias is not None]


def _format_default(value: object, required: bool) -> str:
    if required:
        return "-"
    if value is None:
        return "`None`"
    if isinstance(value, bool):
        return f"`{value}`"
    if isinstance(value, str):
        return f"`{value}`"
    return f"`{json.dumps(value, ensure_ascii=False)}`"


def _clean_multiline(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.strip().splitlines()).strip()


def _compact_whitespace(value: str) -> str:
    return " ".join(value.split())


def _escape_markdown_text(value: str) -> str:
    return value.replace("<", "\\<").replace(">", "\\>")


def _markdown_table_cell(value: str) -> str:
    return _escape_markdown_text(value).replace("|", "\\|").replace("\n", "<br>")


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_bool(value: object) -> bool:
    return value if isinstance(value, bool) else False


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
