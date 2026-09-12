import os
import shutil
from pathlib import Path
from typing import Final

from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_resource_path


_HOOK_TOOL_NAMES: Final[tuple[str, ...]] = ("headroom", "tk", "rtk")


def render_hook_tools(*, console: Console) -> None:
    home_directory = Path.home()
    table = Table(title="Known hook and proxy tools", header_style="bold cyan")
    table.add_column("Tool")
    table.add_column("Executable", overflow="fold")
    table.add_column("Status", overflow="fold")
    incomplete = False
    for name in _HOOK_TOOL_NAMES:
        search_directories: list[str] = []
        for directory in os.get_exec_path():
            try:
                if permitted_resource_path(path=Path(directory) / name, home_directory=home_directory):
                    search_directories.append(directory)
                else:
                    incomplete = True
            except OSError:
                incomplete = True
        executable = shutil.which(name, path=os.pathsep.join(search_directories)) if search_directories else None
        if executable is not None:
            table.add_row(Text(name), Text(executable), "Available on PATH; activation not established")
    if table.row_count:
        console.print(table)
        console.print(
            Text(
                "Hooks, plugins, instructions and provider settings show persisted integrations. PATH presence alone does not mean a tool is active.",
                style="dim",
            )
        )
    if incomplete:
        console.print(Text("Some protected or unreadable PATH locations were excluded from tool discovery.", style="yellow"))
