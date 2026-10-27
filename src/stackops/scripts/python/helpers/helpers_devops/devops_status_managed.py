from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import default_layout_source_paths
from stackops.utils.managed_agent_files import agent_managed_file_locations
from stackops.utils.managed_file_operations import validate_managed_file
from stackops.utils.managed_files import ManagedFileKind, get_managed_file_spec, managed_schema_path

type ManagedFileState = Literal["Valid", "Missing", "Invalid", "Unreadable"]


@dataclass(frozen=True, slots=True)
class ManagedFileStatus:
    name: str
    data_path: Path
    schema_path: Path
    local_schema_path: Path
    state: ManagedFileState
    schema_present: bool
    local_schema_present: bool


def check_managed_files_status() -> list[ManagedFileStatus]:
    names: dict[ManagedFileKind, str] = {
        "config": "StackOps config",
        "layouts": "Terminal layouts",
        "dotfiles": "Dotfile mappings",
        "data": "Backup mappings",
        "secrets": "Secrets",
        "repos": "Repository registry",
        "prompts": "Prompts / contexts",
        "parallel": "Parallel runs",
        "mcp": "MCP catalog",
    }
    statuses: list[ManagedFileStatus] = []
    for kind, name in names.items():
        spec = get_managed_file_spec(kind)
        locations: tuple[tuple[str, Path], ...]
        match kind:
            case "layouts":
                locations = tuple(default_layout_source_paths().items())
            case "secrets":
                from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_secret_sources

                locations = tuple(
                    (source.name, source.path)
                    for source in resolve_secret_sources(secrets_path=None, secrets_source="all")
                )
            case "prompts":
                from stackops.utils.repos.stackops_paths import repo_stackops_yaml_paths

                locations = agent_managed_file_locations(kind=kind)
                known_paths = {path for _, path in locations}
                locations += tuple(
                    (source, path)
                    for source, path in repo_stackops_yaml_paths(path_kind="prompts_yaml")
                    if path not in known_paths
                )
            case "parallel" | "mcp":
                locations = agent_managed_file_locations(kind=kind)
            case _:
                locations = (("", spec.user_path),)
        for source, data_path in locations:
            state: ManagedFileState
            local_schema_path = managed_schema_path(spec=spec, data_path=data_path)
            try:
                if not data_path.exists():
                    state = "Missing"
                elif not data_path.is_file():
                    state = "Invalid"
                else:
                    validate_managed_file(kind=kind, data_path=data_path)
                    state = "Valid"
            except (OSError, UnicodeError):
                state = "Unreadable"
            except ValueError:
                state = "Invalid"
            statuses.append(ManagedFileStatus(
                name=f"""{name} ({source})""" if source else name,
                data_path=data_path,
                schema_path=spec.schema_source_path,
                local_schema_path=local_schema_path,
                state=state,
                schema_present=spec.schema_source_path.is_file(),
                local_schema_present=local_schema_path.is_file(),
            ))
    return statuses


def render_managed_files_status(statuses: list[ManagedFileStatus]) -> Panel:
    table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 1), expand=True, show_lines=True)
    table.add_column("Managed file", style="bold", ratio=1, overflow="fold")
    table.add_column("Status", no_wrap=True)
    table.add_column("File and schemas", ratio=4, overflow="fold")
    for status in statuses:
        paths = Text(str(status.data_path))
        paths.append("\nSchema: ", style="dim")
        paths.append(str(status.schema_path), style="dim" if status.schema_present else "red")
        if not status.schema_present:
            paths.append(" (missing)", style="red")
        paths.append(f"""\nLocal schema ({'present' if status.local_schema_present else 'missing'}): """, style="dim")
        paths.append(str(status.local_schema_path), style="dim")
        state_style = "green" if status.state == "Valid" else "yellow" if status.state == "Missing" else "red"
        table.add_row(Text(status.name), Text(status.state, style=state_style), paths)
    valid = sum(status.state == "Valid" for status in statuses)
    return Panel(
        table,
        title=f"""Managed configuration ({valid}/{len(statuses)} valid)""",
        border_style="cyan",
        padding=(1, 2),
        expand=True,
    )
