from pathlib import Path
from typing import Annotated, Literal

import typer

import stackops.settings.shells.bash as bash_shell_assets
import stackops.settings.shells.pwsh as pwsh_shell_assets
import stackops.settings.shells.zsh as zsh_shell_assets
import stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile as dotfile_module
from stackops.scripts.python.helpers.helpers_devops import cli_config_terminal
from stackops.profile import create_links_export
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.ve import read_default_cloud_config


def config() -> None:
    """🤖 <m> INTERACTIVE configuration of machine."""
    from stackops.scripts.python.helpers.helpers_devops.interactive import main

    main()


def init(
    which: Annotated[
        Literal["init", "ia", "live"], typer.Argument(..., help="Comma-separated list of script names to run all initialization scripts.")
    ] = "init",
    run: Annotated[bool, typer.Option("--run/--no-run", "-r/-nr", help="Run the script after displaying it.")] = False,
) -> None:
    import platform

    script = ""
    if platform.system() == "Linux" or platform.system() == "Darwin":
        match which:
            case "init":
                if platform.system() == "Darwin":
                    init_path = get_path_reference_path(
                        module=zsh_shell_assets,
                        path_reference=zsh_shell_assets.INIT_PATH_REFERENCE,
                    )
                else:
                    init_path = get_path_reference_path(
                        module=bash_shell_assets,
                        path_reference=bash_shell_assets.INIT_PATH_REFERENCE,
                    )
                script = init_path.read_text(encoding="utf-8")
            case "ia":
                import stackops.setup_linux.web_shortcuts as module

                script_path = get_path_reference_path(module=module, path_reference=module.INTERACTIVE_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case "live":
                import stackops.setup_linux.web_shortcuts as module

                script_path = get_path_reference_path(module=module, path_reference=module.LIVE_FROM_GITHUB_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case _:
                typer.echo("Unsupported shell script for Linux.")
                raise typer.Exit(code=1)

    elif platform.system() == "Windows":
        match which:
            case "init":
                init_path = get_path_reference_path(
                    module=pwsh_shell_assets,
                    path_reference=pwsh_shell_assets.INIT_PATH_REFERENCE,
                )
                script = init_path.read_text(encoding="utf-8")
            case "ia":
                import stackops.setup_windows.web_shortcuts as module

                script_path = get_path_reference_path(module=module, path_reference=module.INTERACTIVE_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case "live":
                import stackops.setup_windows.web_shortcuts as module

                script_path = get_path_reference_path(module=module, path_reference=module.LIVE_FROM_GITHUB_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case _:
                typer.echo("Unsupported shell script for Windows.")
                raise typer.Exit(code=1)
    else:
        typer.echo("Unsupported platform for init scripts.")
        raise typer.Exit(code=1)
    if run:
        from stackops.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script, strict=True)
    else:
        print(script)


def dump_config(which: Annotated[Literal["ve"], typer.Option(..., "--which", "-w", help="Which config to dump")]) -> None:
    """🔗 Dump example configuration files."""
    match which:
        case "ve":
            _dump_ve_config()
            return
    msg = typer.style("Error: ", fg=typer.colors.RED) + f"Unknown config type: {which}"
    typer.echo(msg)


def _dump_ve_config() -> None:
    """Generate .ve.example.yaml with all options, sections, comments and default values."""
    cloud_defaults = read_default_cloud_config()

    def to_yaml_value(value: str | bool | None) -> str:
        """Convert Python values to YAML-compatible strings."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        return f'"{value}"'

    yaml_content = f"""# Virtual Environment Configuration File
# This file configures the virtual environment and cloud sync settings for this project
specs:
  ve_path: ".venv"  # Path to the virtual environment directory (e.g., /home/user/projects/myproject/.venv or ~/venvs/myproject)
  ipy_profile: null  # IPython profile name to use when launching IPython (e.g., myprofile creates/uses ~/.ipython/profile_myprofile)
cloud:
  cloud: {to_yaml_value(cloud_defaults["cloud"])}  # Cloud storage identifier/name
  root: {to_yaml_value(cloud_defaults["root"])}  # Root directory within the cloud storage
  rel2home: {to_yaml_value(cloud_defaults["rel2home"])}  # Whether paths are relative to home directory
  pwd: {to_yaml_value(cloud_defaults["pwd"])}  # Password for encryption (leave empty for no password)
  key: {to_yaml_value(cloud_defaults["key"])}  # Encryption key path (leave empty for no key-based encryption)
  encrypt: {to_yaml_value(cloud_defaults["encrypt"])}  # Enable encryption for cloud sync
  os_specific: {to_yaml_value(cloud_defaults["os_specific"])}  # Use OS-specific paths/configuration
  zip: {to_yaml_value(cloud_defaults["zip"])}  # Compress files before uploading
  share: {to_yaml_value(cloud_defaults["share"])}  # Enable sharing/public access
  overwrite: {to_yaml_value(cloud_defaults["overwrite"])}  # Overwrite existing files during sync
"""
    output_path = Path.cwd() / ".ve.example.yaml"
    output_path.write_text(yaml_content, encoding="utf-8")
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Created {output_path}"
    typer.echo(msg)


def copy_assets(which: Annotated[Literal["scripts", "s", "settings", "t", "all", "a"], typer.Argument(..., help="Which assets to copy")]) -> None:
    """🔗 Copy asset files from library to machine."""
    from stackops.profile import create_helper

    match which:
        case "all" | "a":
            create_helper.copy_assets_to_machine(which="scripts")
            create_helper.copy_assets_to_machine(which="settings")
            return
        case "scripts" | "s":
            create_helper.copy_assets_to_machine(which="scripts")
            return
        case "settings" | "t":
            create_helper.copy_assets_to_machine(which="settings")
            return
    msg = typer.style("Error: ", fg=typer.colors.RED) + f"Unknown asset type: {which}"
    typer.echo(msg)


def get_app() -> typer.Typer:
    config_apps = typer.Typer(help="🧰 <c> configuration subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)

    config_apps.command("config", no_args_is_help=False, help="🤖 <m> Interactive configuration of machine.")(config)
    config_apps.command("m", no_args_is_help=False, help="Interactive configuration of machine.", hidden=True)(config)

    config_apps.command("init", no_args_is_help=False, help="🦐 <I> Define and manage configurations.")(init)
    config_apps.command("I", no_args_is_help=False, help="Define and manage configurations.", hidden=True)(init)

    config_apps.command("sync", no_args_is_help=True, help="🔄 <s> Sync dotfiles.")(create_links_export.main_from_parser)
    config_apps.command("s", no_args_is_help=True, help="Sync dotfiles.", hidden=True)(create_links_export.main_from_parser)

    config_apps.command("register", no_args_is_help=True, help="📇 <r> Register dotfiles against user mapper.yaml")(dotfile_module.register_dotfile)
    config_apps.command("r", no_args_is_help=True, hidden=True)(dotfile_module.register_dotfile)
    config_apps.command("edit", no_args_is_help=True, help="📝 <E> Open dotfiles mapper.yaml in nano, hx, or code.")(dotfile_module.edit_dotfile)
    config_apps.command("E", no_args_is_help=True, help="Open dotfiles mapper.yaml in nano, hx, or code.", hidden=True)(dotfile_module.edit_dotfile)

    config_apps.command("export-dotfiles", no_args_is_help=True, help="📤 <e> Export dotfiles for migration to new machine.")(
        dotfile_module.export_dotfiles
    )
    config_apps.command("e", no_args_is_help=True, help="Export dotfiles for migration to new machine.", hidden=True)(dotfile_module.export_dotfiles)
    config_apps.command("import-dotfiles", no_args_is_help=False, help="📥 <i> Import dotfiles from exported archive.")(
        dotfile_module.import_dotfiles
    )
    config_apps.command("i", no_args_is_help=False, help="Import dotfiles from exported archive.", hidden=True)(dotfile_module.import_dotfiles)

    config_apps.add_typer(cli_config_terminal.get_app(), name="terminal", help="🐚 <t> Configure your terminal profile.")
    config_apps.add_typer(cli_config_terminal.get_app(), name="t", help="🐚 <t> Configure your terminal profile.", hidden=True)

    config_apps.command("copy-assets", no_args_is_help=True, help="📋 <c> Copy asset files from library to machine.", hidden=False)(copy_assets)
    config_apps.command("c", no_args_is_help=True, help="Copy asset files from library to machine.", hidden=True)(copy_assets)

    config_apps.command("dump", no_args_is_help=True, help="📦 <d> Dump example configuration files.")(dump_config)
    config_apps.command("d", no_args_is_help=True, help="Dump example configuration files.", hidden=True)(dump_config)

    return config_apps
