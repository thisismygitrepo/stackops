from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import stackops.utils.path_core as path_core
from stackops.profile.create_links import ConfigMapper, read_mapper
from stackops.profile.linking.operations import files_are_identical
from stackops.utils.source_of_truth import resolve_source_of_truth_path

type ConfigMethod = Literal["link", "copy", "contents"]
type ConfigMappingState = Literal[
    "Configured",
    "Missing default path",
    "Missing managed path",
    "Missing both paths",
    "Expected directories",
    "Link mismatch",
    "Copy differs",
    "Contents differ",
    "Not configured",
]


@dataclass(frozen=True)
class ConfigFileStatus:
    program: str
    file_name: str
    method: ConfigMethod
    configured: bool
    status: ConfigMappingState
    default_path: str
    managed_path: str


class ConfigFilesStatus(TypedDict):
    count: int
    linked: int
    program_count: int
    configs: list[str]
    items: list[ConfigFileStatus]


def _copied_paths_are_identical(default_path: Path, managed_path: Path) -> bool:
    if default_path.is_file() and managed_path.is_file():
        return files_are_identical(default_path, managed_path)
    if not default_path.is_dir() or not managed_path.is_dir():
        return False
    default_children = {child.name: child for child in default_path.iterdir()}
    managed_children = {child.name: child for child in managed_path.iterdir()}
    return default_children.keys() == managed_children.keys() and all(
        _copied_paths_are_identical(default_children[name], managed_child)
        for name, managed_child in managed_children.items()
    )


def _check_mapping_paths(default_path: Path, managed_path: Path, *, contents: bool, copy: bool) -> ConfigMappingState:
    default_exists = default_path.exists()
    managed_exists = managed_path.exists()
    if not default_exists and not managed_exists:
        return "Missing both paths"
    if not default_exists:
        return "Missing default path"
    if not managed_exists:
        return "Missing managed path"
    if contents:
        if not default_path.is_dir() or not managed_path.is_dir():
            return "Expected directories"
        configured = all(
            _check_mapping_paths(default_path.joinpath(child.name), child, contents=False, copy=copy) == "Configured"
            for child in managed_path.iterdir()
        )
        return "Configured" if configured else "Contents differ"
    if path_core.resolve(default_path, strict=False) == path_core.resolve(managed_path, strict=False):
        return "Configured"
    if default_path.is_symlink():
        return "Link mismatch"
    if copy:
        return "Configured" if _copied_paths_are_identical(default_path, managed_path) else "Copy differs"
    return "Not configured"


def _check_config_file(program: str, config_item: ConfigMapper) -> ConfigFileStatus:
    default_path = Path(config_item["config_file_default_path"]).expanduser()
    managed_path = resolve_source_of_truth_path(config_item["config_file_self_managed_path"])
    method: ConfigMethod = "contents" if config_item["contents"] else ("copy" if config_item["copy"] else "link")
    state = _check_mapping_paths(default_path, managed_path, contents=bool(config_item["contents"]), copy=bool(config_item["copy"]))
    return ConfigFileStatus(
        program=program,
        file_name=config_item["file_name"],
        method=method,
        configured=state == "Configured",
        status=state,
        default_path=str(default_path),
        managed_path=str(managed_path),
    )


def check_config_files_status() -> ConfigFilesStatus:
    mapper = read_mapper(source="all")
    items = [
        _check_config_file(program, config_item)
        for program, configs in mapper.items()
        for config_item in configs
    ]
    return {
        "count": len(items),
        "linked": sum(item.configured for item in items),
        "program_count": len(mapper),
        "configs": list(mapper),
        "items": items,
    }


def render_config_files_status(status: ConfigFilesStatus) -> Panel:
    percentage = status["linked"] / status["count"] * 100 if status["count"] else 0
    summary = Table(show_header=True, box=None, padding=(0, 2), expand=False)
    summary.add_column("Configured", justify="right")
    summary.add_column("Mapped", justify="right")
    summary.add_column("Progress", justify="right")
    summary.add_row(str(status["linked"]), str(status["count"]), f"""{percentage:.0f}%""")

    details = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 1), expand=True, show_lines=True)
    details.add_column("Program / mapping", style="bold", ratio=1, overflow="fold")
    details.add_column("Method", no_wrap=True)
    details.add_column("Status", ratio=1, overflow="fold")
    details.add_column("Default path", ratio=2, overflow="fold")
    details.add_column("Managed path", ratio=2, overflow="fold")
    for item in status["items"]:
        program = Text(item.program, style="bold")
        program.append(f"""\n{item.file_name}""", style="dim")
        details.add_row(
            program,
            item.method,
            Text(item.status, style="green" if item.configured else "yellow"),
            Text(item.default_path),
            Text(item.managed_path),
        )

    border_style = "green" if percentage > 80 else ("yellow" if percentage > 50 else "red")
    content = Group(summary, "", details if status["items"] else Text("No configuration file mappings for this operating system."))
    return Panel(
        content,
        title=f"""Configuration Files ({percentage:.0f}% configured)""",
        border_style=border_style,
        padding=(1, 2),
        expand=True,
    )
