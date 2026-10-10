import typer

DOTFILES_HELP = "Sync, register, export, and import dotfiles listed in the user mapper/dotfiles.yaml."


def get_app() -> typer.Typer:
    from stackops.profile import create_links_export
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import register_dotfile
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer import export_dotfiles, import_dotfiles

    app = typer.Typer(
        help=DOTFILES_HELP, no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command("sync", no_args_is_help=True, help="🔄 <s> Sync dotfiles between their original paths and the dotfiles repo.")(create_links_export.main_from_parser)
    app.command("s", no_args_is_help=True, help="Sync dotfiles.", hidden=True)(create_links_export.main_from_parser)
    app.command("register", no_args_is_help=True, help="📇 <r> Register a dotfile in the user mapper/dotfiles.yaml.")(register_dotfile)
    app.command("r", no_args_is_help=True, help="Register a dotfile.", hidden=True)(register_dotfile)
    app.command("export", no_args_is_help=True, help="📤 <e> Export dotfiles for migration to a new machine.")(export_dotfiles)
    app.command("e", no_args_is_help=True, help="Export dotfiles.", hidden=True)(export_dotfiles)
    app.command("import", no_args_is_help=False, help="📥 <i> Import dotfiles from an exported archive.")(import_dotfiles)
    app.command("i", no_args_is_help=False, help="Import dotfiles.", hidden=True)(import_dotfiles)
    return app
