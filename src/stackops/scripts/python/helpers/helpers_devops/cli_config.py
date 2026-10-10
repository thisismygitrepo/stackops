from typing import Annotated, Literal

import typer

from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cli_utils.ordered_group import ordered_group


def config() -> None:
    """🤖 <I> interactive configuration of machine."""
    from stackops.scripts.python.helpers.helpers_devops.interactive import main

    main()


def terminal(ctx: typer.Context) -> None:
    """🐚 <t> Configure your terminal profile."""
    from stackops.scripts.python.helpers.helpers_devops import cli_config_terminal

    apply_alias_markers(cli_config_terminal.get_app())(ctx.args, prog_name=ctx.command_path, standalone_mode=False)


def copy_assets(which: Annotated[Literal["scripts", "s", "settings", "t", "all", "a"], typer.Argument(..., help="Which assets to copy")]) -> None:
    """🔗 Copy asset files from library to machine.

    Strict behavior:
    - Raise typer.Exit(code=1) on unknown asset type or on any failure.
    - Exit immediately on first failure when copying multiple asset groups.
    """
    from stackops.profile import create_helper

    try:
        match which:
            case "all" | "a":
                create_helper.copy_assets_to_machine(which="scripts")
                create_helper.copy_assets_to_machine(which="settings")
                typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + "Copied all assets.")
                return
            case "scripts" | "s":
                create_helper.copy_assets_to_machine(which="scripts")
                typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + "Copied script assets.")
                return
            case "settings" | "t":
                create_helper.copy_assets_to_machine(which="settings")
                typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + "Copied settings assets.")
                return
    except Exception as exc:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"Failed to copy assets ({which}): {exc}")
        raise typer.Exit(code=1) from exc

    # Unreachable with current Literal type, but keep strict behavior if it occurs.
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"Unknown asset type: {which}")
    raise typer.Exit(code=1)


def get_app() -> typer.Typer:
    import stackops.scripts.python.helpers.helpers_devops.cli_config_dotfiles as dotfiles_module
    import stackops.scripts.python.helpers.helpers_devops.cli_config_setup as setup_module
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dump import DUMP_HELP, dump_config
    from stackops.scripts.python.helpers.helpers_devops.cli_config_edit import EDIT_HELP, edit_managed_file
    from stackops.scripts.python.helpers.helpers_devops.cli_config_init_script import INIT_SCRIPT_HELP, init_script

    config_apps = typer.Typer(
        cls=ordered_group(("dotfiles", "setup", "edit", "dump", "init-script", "terminal", "interactive", "copy-assets")),
        help="🧰 <c> configuration subcommands", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }

    config_apps.add_typer(dotfiles_module.get_app(), name="dotfiles", help=f"🗂 <f> {dotfiles_module.DOTFILES_HELP}")
    config_apps.add_typer(dotfiles_module.get_app(), name="f", help=dotfiles_module.DOTFILES_HELP, hidden=True)

    config_apps.add_typer(setup_module.get_app(), name="setup", help=f"🧭 <u> {setup_module.SETUP_HELP}")
    config_apps.add_typer(setup_module.get_app(), name="u", help=setup_module.SETUP_HELP, hidden=True)

    config_apps.command("edit", no_args_is_help=True, help=f"📝 <e> {EDIT_HELP}")(edit_managed_file)
    config_apps.command("e", no_args_is_help=True, help=EDIT_HELP, hidden=True)(edit_managed_file)

    config_apps.command("dump", no_args_is_help=True, help=f"📦 <d> {DUMP_HELP}")(dump_config)
    config_apps.command("d", no_args_is_help=True, help=DUMP_HELP, hidden=True)(dump_config)

    config_apps.command("init-script", no_args_is_help=True, help=f"🚀 <n> {INIT_SCRIPT_HELP}")(init_script)
    config_apps.command("n", no_args_is_help=True, help=INIT_SCRIPT_HELP, hidden=True)(init_script)

    config_apps.command("terminal", help="🐚 <t> Configure your terminal profile.", context_settings=ctx_settings)(terminal)
    config_apps.command("t", help="🐚 <t> Configure your terminal profile.", hidden=True, context_settings=ctx_settings)(terminal)

    config_apps.command("interactive", no_args_is_help=False, help="🤖 <i> Interactive configuration of machine.")(config)
    config_apps.command("i", no_args_is_help=False, help="Interactive configuration of machine.", hidden=True)(config)

    config_apps.command("copy-assets", no_args_is_help=True, help="📋 <c> Copy asset files from library to machine.", hidden=False)(copy_assets)
    config_apps.command("c", no_args_is_help=True, help="Copy asset files from library to machine.", hidden=True)(copy_assets)

    return config_apps
