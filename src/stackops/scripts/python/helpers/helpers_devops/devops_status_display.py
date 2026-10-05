"""Machine status output rendering."""

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_devops.devops_status_apps import render_tools_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_backup import BackupStatus, render_backup_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_checks import ShellProfileStatus, SshStatus
from stackops.scripts.python.helpers.helpers_devops.devops_status_config import ConfigFilesStatus, render_config_files_status


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


def render_shell_status(status: ShellProfileStatus) -> Panel:
    left_table = Table(show_header=False, box=None, padding=(0, 1))
    left_table.add_column("Item", style="cyan", no_wrap=True)
    left_table.add_column("Status")

    left_table.add_row("📄 Profile", Text(str(status["profile_path"])))
    left_table.add_row(f"{'✅' if status['exists'] else '❌'} Exists", str(status["exists"]))
    left_table.add_row(f"{'✅' if status['configured'] else '❌'} Configured", str(status["configured"]))

    right_table = Table(show_header=False, box=None, padding=(0, 1))
    right_table.add_column("Item", style="cyan", no_wrap=True)
    right_table.add_column("Status")

    right_table.add_row("📄 Init script", Text(status["init_script_path"]))
    right_table.add_row(f"{'✅' if status['source_line_present'] else '❌'} Source line", str(status["source_line_present"]))
    right_table.add_row(f"{'✅' if status['init_script_exists'] else '❌'} Init exists", str(status["init_script_exists"]))

    border_style = "green" if status["configured"] else "yellow"
    return Panel(
        Columns([left_table, right_table], equal=True, expand=True),
        title="Shell Profile",
        border_style=border_style,
        padding=(1, 2),
        expand=False,
    )


def render_ssh_status(status: SshStatus) -> Panel | Columns:
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


def display_shell_status(status: ShellProfileStatus) -> None:
    console.rule("[bold green]🐚 Shell Profile[/bold green]")
    console.print(render_shell_status(status))


def display_ssh_status(status: SshStatus) -> None:
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
