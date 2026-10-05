from rich import box
from rich.console import Group
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.installer_runner import get_installers_from_source
from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name


def check_important_tools() -> dict[str, dict[str, bool]]:
    installers = get_installers_from_source(source="all", os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    group_status: dict[str, dict[str, bool]] = {}
    for installer_data in installers:
        executable_name = Installer(installer_data=installer_data).get_exe_name()
        installed = check_tool_exists(tool_name=executable_name)
        for category_label in installer_data["categoryLabels"]:
            group_status.setdefault(category_label, {})[installer_data["appName"]] = installed

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
