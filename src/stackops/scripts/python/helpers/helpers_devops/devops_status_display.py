"""Machine status output rendering."""

from typing import Any

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_devops.devops_status_apps import render_tools_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_backup import BackupStatus, render_backup_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_config import ConfigFilesStatus, render_config_files_status
from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH


console = Console()


def display_report_header() -> None:
    """Display report header."""
    console.print("\n")
    console.print(Panel(Text("📊 Machine Status Report", justify="center", style="bold white"), style="bold blue", padding=(1, 2)))
    console.print("\n")


def display_report_footer() -> None:
    """Display report footer."""
    console.print("\n")
    console.print(Panel(Text("✨ Status report complete!", justify="center", style="bold green"), style="green", padding=(1, 2)))
    console.print("\n")


def render_system_info(info: dict[str, str]) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("🏠 Hostname", Text(info["hostname"]))
    table.add_row("💿 System", Text(f"""{info['system']} {info['release']}"""))
    table.add_row("🖥️  Machine", Text(info["machine"]))
    table.add_row("⚙️  Processor", Text(info["processor"]))
    table.add_row("🐍 Python", Text(info["python_version"]))
    table.add_row("👤 User", Text(info["user"]))

    return Panel(table, title="System", border_style="blue", padding=(1, 2), expand=False)


def render_shell_status(status: dict[str, Any]) -> Panel:
    if "error" in status:
        return Panel(Text(f"""❌ Error: {status['error']}"""), title="Shell Profile", border_style="red", padding=(1, 2), expand=False)

    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("Item", style="cyan", no_wrap=True)
    left_table.add_column("Status")

    left_table.add_row("📄 Profile", Text(str(status["profile_path"])))
    left_table.add_row(f"{'✅' if status['exists'] else '❌'} Exists", str(status["exists"]))
    left_table.add_row(f"{'✅' if status['configured'] else '❌'} Configured", str(status["configured"]))

    right_table = Table(show_header=False, box=None, padding=(0, 1))
    right_table.add_column("Item", style="cyan", no_wrap=True)
    right_table.add_column("Status")

    right_table.add_row("🔧 Method", Text(str(status["method"])))
    right_table.add_row(f"{'✅' if status['init_script_exists'] else '❌'} Init (source)", str(status["init_script_exists"]))
    right_table.add_row(f"{'✅' if status['init_script_copy_exists'] else '❌'} Init (copy)", str(status["init_script_copy_exists"]))

    border_style = "green" if status["configured"] else "yellow"
    return Panel(
        Columns([left_table, right_table], equal=True, expand=True),
        title="Shell Profile",
        border_style=border_style,
        padding=(1, 2),
        expand=False,
    )


def render_repos_status(status: dict[str, Any]) -> Panel:
    if not status["configured"]:
        return Panel(Text(f"""⚠️  No repositories configured in {DOTFILES_STACKOPS_CONFIG_PATH}"""), title="Repositories", border_style="yellow", padding=(1, 2))

    if status["count"] == 0:
        return Panel("ℹ️  No repositories configured", title="Repositories", border_style="blue", padding=(1, 2))

    table = Table(show_lines=True, header_style="bold cyan")
    table.add_column("Repository", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    for repo in status["repos"]:
        name = repo["name"]
        if not repo["exists"]:
            table.add_row(Text(f"""❌ {name}"""), "Missing", Text(f"""Path: {repo['path']}"""))
        elif not repo["is_repo"]:
            table.add_row(Text(f"""⚠️  {name}"""), "Not a repo", Text(f"""Path: {repo['path']}"""))
        else:
            status_icon = "✅" if repo["clean"] else "⚠️"
            status_text = "Clean" if repo["clean"] else "Uncommitted changes"
            table.add_row(Text(f"""{status_icon} {name}"""), status_text, Text(f"""Branch: {repo['branch']}"""))

    return Panel(table, title=f"""Repositories ({status['count']})""", border_style="cyan", padding=(1, 2))


def render_ssh_status(status: dict[str, Any]) -> Panel | Columns:
    if not status["ssh_dir_exists"]:
        return Panel("❌ SSH directory (~/.ssh) does not exist", title="SSH Status", border_style="red", padding=(1, 2), expand=False)

    config_table = Table(show_header=False, box=None, padding=(0, 1))
    config_table.add_column("Item", style="cyan", no_wrap=True)
    config_table.add_column("Status")

    config_table.add_row("📁 Directory", Text(str(status["ssh_dir_path"])))
    config_table.add_row(f"{'✅' if status['config_exists'] else '❌'} Config", str(status["config_exists"]))
    config_table.add_row(f"{'✅' if status['authorized_keys_exists'] else '❌'} Auth Keys", str(status["authorized_keys_exists"]))
    config_table.add_row(f"{'✅' if status['known_hosts_exists'] else '❌'} Known Hosts", str(status["known_hosts_exists"]))

    config_panel = Panel(config_table, title="SSH Config", border_style="yellow", padding=(1, 2), expand=False)

    if status["keys"]:
        keys_table = Table(show_header=True, box=None, padding=(0, 1), show_lines=False, expand=False)
        keys_table.add_column("Key Name", style="bold cyan")
        keys_table.add_column("Pub", justify="center")
        keys_table.add_column("Priv", justify="center")

        for key in status["keys"]:
            pub_status = "✅" if key["public_exists"] else "❌"
            priv_status = "✅" if key["private_exists"] else "❌"
            keys_table.add_row(Text(str(key["name"])), pub_status, priv_status)

        keys_panel = Panel(keys_table, title=f"SSH Keys ({len(status['keys'])})", border_style="yellow", padding=(1, 2), expand=False)

        return Columns([config_panel, keys_panel], equal=False, expand=True)
    return config_panel


def display_system_info(info: dict[str, str]) -> None:
    console.rule("[bold blue]💻 System Information[/bold blue]")
    console.print(render_system_info(info))


def display_shell_status(status: dict[str, Any]) -> None:
    console.rule("[bold green]🐚 Shell Profile[/bold green]")
    console.print(render_shell_status(status))


def display_repos_status(status: dict[str, Any]) -> None:
    console.rule("[bold cyan]📚 Configured Repositories[/bold cyan]")
    console.print(render_repos_status(status))


def display_ssh_status(status: dict[str, Any]) -> None:
    console.rule("[bold yellow]🔐 SSH Configuration[/bold yellow]")
    console.print(render_ssh_status(status))


def display_config_files_status(status: ConfigFilesStatus) -> None:
    console.rule("[bold bright_blue]⚙️  Configuration Files[/bold bright_blue]")
    console.print(render_config_files_status(status))


def display_tools_status(grouped_tools: dict[str, dict[str, bool]]) -> None:
    console.print(render_tools_status(grouped_tools))


def display_backup_status(status: BackupStatus) -> None:
    console.rule("[bold bright_cyan]💾 Backup Configuration[/bold bright_cyan]")
    console.print(render_backup_status(status))
