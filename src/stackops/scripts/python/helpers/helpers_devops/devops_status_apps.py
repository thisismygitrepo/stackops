import shutil

from rich import box
from rich.console import Group
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


def check_important_tools() -> dict[str, dict[str, bool]]:
    from stackops.utils.schemas.installer.package_groups import PACKAGE_GROUP2NAMES

    group_status: dict[str, dict[str, bool]] = {}
    for group_name, tools in PACKAGE_GROUP2NAMES.items():
        tool_status: dict[str, bool] = {}
        for tool in tools:
            tool_status[tool] = shutil.which(tool) is not None
        group_status[group_name] = tool_status

    return group_status


def render_tools_status(grouped_tools: dict[str, dict[str, bool]]) -> Group:
    unique_tool_status = {tool: installed for tools in grouped_tools.values() for tool, installed in tools.items()}
    installed_tool_names = sorted(tool for tool, installed in unique_tool_status.items() if installed)
    not_installed_tool_names = sorted(tool for tool, installed in unique_tool_status.items() if not installed)

    section_title = Text("Apps installed", style="bold cyan")
    section_title.append(f""" · {len(installed_tool_names)} installed · {len(unique_tool_status)} in catalog""")

    table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", padding=(0, 1), expand=True)
    table.add_column("Group", style="bold cyan", overflow="fold")
    table.add_column("Installed", justify="right")
    table.add_column("Not installed", justify="right")

    for group_name, tools in grouped_tools.items():
        installed_count = sum(tools.values())
        group_display_name = group_name.replace("_", " ").replace("-", " ").title()
        table.add_row(Text(group_display_name), str(installed_count), str(len(tools) - installed_count))

    installed_summary = Text(f"""Installed apps ({len(installed_tool_names)}): """, style="bold")
    installed_summary.append(", ".join(installed_tool_names) if installed_tool_names else "None", style="not bold")
    not_installed_summary = Text(f"""Not installed apps ({len(not_installed_tool_names)}): """, style="bold")
    not_installed_summary.append(", ".join(not_installed_tool_names) if not_installed_tool_names else "None", style="not bold")
    return Group(Rule(section_title), table, installed_summary, not_installed_summary)
