#!/usr/bin/env python3
"""
Interactive Machine Configuration Setup Script


TODO: add option for importing dotfiles
"""

import sys
from pathlib import Path
import platform
from typing import Literal
import questionary
from questionary import Choice
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from stackops.utils.code import run_shell_script

InstallOption = Literal[
    "install_stackops",
    "sysabc",
    "termabc",
    "install_shell_profile",
    "link_public_configs",
    "link_private_configs",
    "retrieve_repositories",
    "retrieve_data",
]

console = Console()


def display_header() -> None:
    from stackops.utils.installer_utils.installer_runner import get_stackops_version
    from rich.align import Align

    # Fancy ASCII art header
    ascii_art = """
    ╔═════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
    ║                                                                                                             ║
    ║   ███╗   ███╗ █████╗  ██████╗██╗  ██╗██╗███╗   ██╗███████╗ ██████╗ ██████╗ ███╗   ██╗███████╗██╗ ██████╗    ║
    ║   ████╗ ████║██╔══██╗██╔════╝██║  ██║██║████╗  ██║██╔════╝██╔════╝██╔═══██╗████╗  ██║██╔════╝██║██╔════╝    ║
    ║   ██╔████╔██║███████║██║     ███████║██║██╔██╗ ██║█████╗  ██║     ██║   ██║██╔██╗ ██║█████╗  ██║██║  ███╗   ║
    ║   ██║╚██╔╝██║██╔══██║██║     ██╔══██║██║██║╚██╗██║██╔══╝  ██║     ██║   ██║██║╚██╗██║██╔══╝  ██║██║   ██║   ║
    ║   ██║ ╚═╝ ██║██║  ██║╚██████╗██║  ██║██║██║ ╚████║███████╗╚██████╗╚██████╔╝██║ ╚████║██║     ██║╚██████╔╝   ║
    ║   ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚═╝ ╚═════╝    ║
    ║                                                                                                             ║
    ╚═════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
    """

    version = get_stackops_version()
    title = f"✨ MACHINE CONFIGURATION v{version} ✨"
    subtitle = "🎯 Your digital life manager. Dotfiles, data, code and more."
    bug_report = "🐛 Please report bugs @ https://github.com/thisismygitrepo/stackops"

    # Print ASCII art
    console.print(Text(ascii_art, style="bold cyan"))
    console.print()
    
    # Print centered text elements
    console.print(Align.center(Text(title, style="bold bright_magenta")))
    console.print(Align.center(Text(subtitle, style="italic bright_blue")))
    console.print()
    console.print(Align.center(Text(bug_report, style="dim white")))
    console.print()


def get_installation_choices() -> list[InstallOption]:
    """Get user choices for installation options."""
    v0: InstallOption = "install_stackops"
    v1: InstallOption = "sysabc"
    v2: InstallOption = "termabc"
    v3: InstallOption = "install_shell_profile"
    v5: InstallOption = "retrieve_repositories"
    v6: InstallOption = "retrieve_data"
    v7: InstallOption = "link_public_configs"
    v8: InstallOption = "link_private_configs"
    choices = [
        Choice(value=v0, title="🐍 Install stackops cli.", checked=False),
        Choice(value=v1, title="📥 Install ABCs: package manager, then git, then bun.", checked=False),
        Choice(value=v2, title="⚡ Install Terminal CLI apps essentials (group `termabc`)", checked=False),
        Choice(value=v3, title="🐚 Configure Shell Profile Init.", checked=False),
        Choice(value=v7, title="🔗 Link Public Configs (symlink public dotfiles).", checked=False),
        Choice(value=v8, title="🔐 [ADVANCED] Link Private Configs (symlink private dotfiles).", checked=False),
        Choice(value=v5, title="📚 [ADVANCED] Retrieve Repositories", checked=False),
        Choice(value=v6, title="💾 [ADVANCED] Retrieve Data.", checked=False),
    ]
    selected: list[InstallOption] = questionary.checkbox("Select the installation options you want to execute:", choices=choices, show_description=True).ask() or []
    return selected


def execute_installations(selected_options: list[InstallOption]) -> None:
    for maybe_a_group in selected_options:
        if maybe_a_group in ("termabc", "sysabc"):
            console.print(Panel("⚡ [bold bright_yellow]CLI APPLICATIONS[/bold bright_yellow]\n[italic]Command-line tools installation[/italic]", border_style="bright_yellow"))
            console.print("🔧 Installing CLI applications", style="bold cyan")
            try:
                from stackops.utils.installer_utils.installer_cli import main_installer_cli as devops_devapps_install_main
                devops_devapps_install_main(group=True, which=maybe_a_group, interactive=False)
                console.print("✅ CLI applications installed successfully", style="bold green")
            except Exception as e:
                console.print(f"❌ Error installing CLI applications: {e}", style="bold red")
            if platform.system() == "Linux":
                shell_profile = ". $HOME/.bashrc"
            elif platform.system() == "Darwin":
                shell_profile = ". $HOME/.zshrc"
            elif platform.system() == "Windows":
                shell_profile = None
            else:
                shell_profile = None
            if shell_profile is not None:
                try:
                    console.print("🔄 Reloading shell profile to apply changes", style="bold cyan")
                    run_shell_script(shell_profile, display_script=False, clean_env=False)
                    console.print("✅ Shell profile reloaded successfully", style="bold green")
                except Exception as e:
                    console.print(f"❌ Error reloading shell profile: {e}", style="bold red")

    if "install_stackops" in selected_options:
        console.print(Panel("🐍 [bold green]PYTHON ENVIRONMENT[/bold green]\n[italic]Virtual environment setup[/italic]", border_style="green"))
        from stackops.scripts.python.helpers.helpers_devops.cli_self import install
        install(dev=False)

    if "install_shell_profile" in selected_options:
        console.print(Panel("🐚 [bold green]SHELL PROFILE[/bold green]\n[italic]Shell configuration setup[/italic]", border_style="green"))
        console.print("🔧 Configuring shell profile", style="bold cyan")
        try:
            from stackops.profile.create_shell_profile import create_default_shell_profile
            create_default_shell_profile()
            console.print("✅ Shell profile configured successfully", style="bold green")
            from stackops.profile.create_links_export import main_from_parser
            main_from_parser(direction="down", sensitivity="public", method="copy", on_conflict="overwrite-default-path", which="all")
            if platform.system() == "Windows":
                from stackops.jobs.installer.python_scripts.nerfont_windows_helper import install_nerd_fonts
                install_nerd_fonts()
                from stackops.settings.wt.set_wt_settings import main as set_wt_settings_main
                set_wt_settings_main()
        except Exception as e:
            console.print(f"❌ Error configuring shell profile: {e}", style="bold red")

    if "link_public_configs" in selected_options:
        console.print(Panel("🔗 [bold bright_green]LINK PUBLIC CONFIGS[/bold bright_green]\n[italic]Symlinking public dotfiles[/italic]", border_style="bright_green"))
        console.print("🔧 Linking public configs", style="bold cyan")
        try:
            from stackops.profile.create_links_export import main_from_parser
            from stackops.profile.create_helper import copy_assets_to_machine

            copy_assets_to_machine(which="settings")
            main_from_parser(direction="down", sensitivity="public", method="symlink", on_conflict="overwrite-default-path", which="all")
            console.print("✅ Public configs linked successfully", style="bold green")
        except Exception as e:
            console.print(f"❌ Error linking public configs: {e}", style="bold red")

    require_dotfiles: list[InstallOption] = [
        "retrieve_repositories", "retrieve_data", "link_private_configs"]
    if any(a_selected in require_dotfiles for a_selected in selected_options):
        # we cannot proceed before dotfiles are in place
        if Path.home().joinpath("dotfiles").exists():
            console.print("✅ Dotfiles directory found.", style="bold green")
        else:
            header_text = Text("DOTFILES MIGRATION", style="bold yellow")
            subtitle_text = Text("Configuration transfer options", style="italic yellow")
            instructions = """
            On remote, run:
            devops config export-dotfiles --password pwd
            On new machine, run:
            devops config import-dotfiles --password pwd
            """
            console.print(Panel(f"📂 {header_text}\n{subtitle_text}\n\n{instructions}", border_style="yellow", padding=(1, 2)))
            i_sorted_it_out = "I have sorted out dotfiles migration already and want to proceed."
            exit_now = "Exit now and sort out dotfiles migration first."
            fetch_over_lan = "I already exposed dotfiles over LAN, let's fetch them now."
            fetch_over_ssh = "I wanted to bring them using SSH SCP now."
            options: list[str] = [
                i_sorted_it_out,
                exit_now,
                fetch_over_lan,
                fetch_over_ssh,
            ]
            answer = questionary.select("⚠️  DOTFILES NOT FOUND. How do you want to proceed?", choices=options).ask()
            if answer == i_sorted_it_out:
                console.print("✅ Proceeding as per user confirmation.", style="bold green")
            elif answer == exit_now:
                console.print("❌ Exiting for dotfiles migration.", style="bold red")
                sys.exit(0)
            elif answer == fetch_over_lan:
                from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile import import_dotfiles
                import_dotfiles(use_ssh=False)
            elif answer == fetch_over_ssh:
                from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile import import_dotfiles
                import_dotfiles(use_ssh=True)
            if not Path.home().joinpath("dotfiles").exists():
                console.print("❌ Dotfiles directory still not found after attempted import. Exiting...", style="bold red")
                sys.exit(1)

    if "link_private_configs" in selected_options:
        console.print(Panel("🔐 [bold bright_red]LINK PRIVATE CONFIGS[/bold bright_red]\n[italic]Symlinking private dotfiles[/italic]", border_style="bright_red"))
        console.print("🔧 Linking private configs", style="bold cyan")
        try:
            from stackops.profile.create_links_export import main_from_parser
            main_from_parser(direction="down", sensitivity="private", method="symlink", on_conflict="overwrite-default-path", which="all")
            console.print("✅ Private configs linked successfully", style="bold green")
        except Exception as e:
            console.print(f"❌ Error linking private configs: {e}", style="bold red")

    if "retrieve_repositories" in selected_options:
        console.print(Panel("📚 [bold bright_magenta]REPOSITORIES[/bold bright_magenta]\n[italic]Project code retrieval[/italic]", border_style="bright_magenta"))
        from stackops.scripts.python.helpers.helpers_devops import cli_repos
        cli_repos.clone(interactive=True)

    if "retrieve_data" in selected_options:
        console.print(Panel("💾 [bold bright_cyan]DATA RETRIEVAL[/bold bright_cyan]\n[italic]Backup restoration[/italic]", border_style="bright_cyan"))
        console.print("🔧 Retrieving backup data", style="bold cyan")
        try:
            from stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve import main_backup_retrieve
            main_backup_retrieve(direction="RETRIEVE", cloud=None, which=None, repo="all")
            console.print("✅ Backup data retrieved successfully", style="bold green")
        except Exception as e:
            console.print(f"❌ Error retrieving backup data: {e}", style="bold red")


def main() -> None:
    display_header()
    selected_options = get_installation_choices()
    if not selected_options:
        console.print("❌ No options selected. Exiting...", style="bold red")
        sys.exit(0)
    console.print(f"\n✅ Selected options: {'\n'.join(selected_options)}", style="bold green")
    proceed = questionary.confirm("🚀 Proceed with installation?", default=True).ask()
    if not proceed:
        console.print("❌ Installation cancelled.", style="bold red")
        sys.exit(0)
    execute_installations(selected_options=selected_options)
    completion_text = Text("INSTALLATION COMPLETE", style="bold green")
    subtitle_text = Text("System setup finished successfully", style="italic green")
    console.print(Panel(f"✨ {completion_text}\n{subtitle_text}\n\n🎉 Your system has been configured successfully!\n🔄 You may need to reboot to apply all changes.", border_style="green", padding=(1, 2)))

    from stackops.profile.create_shell_profile import reload_shell_profile_and_exit
    reload_shell_profile_and_exit()



if __name__ == "__main__":
    pass
