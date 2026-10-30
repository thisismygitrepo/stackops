import typer

DOTFILES_HELP = "Sync packaged settings and user dotfiles; collect, register, export, and import user dotfiles."


def get_app() -> typer.Typer:
    from stackops.profile import create_links_export
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_collect import COLLECT_HELP, collect_dotfiles
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import register_dotfile
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer import export_dotfiles, import_dotfiles
    from stackops.utils.managed_file_commands import register_managed_file_commands

    app = typer.Typer(
        help=DOTFILES_HELP, no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command("sync", no_args_is_help=True, help="🔄 <s> Sync mapped files between their original and managed paths.")(create_links_export.main_from_parser)
    app.command("s", no_args_is_help=True, help="Sync dotfiles.", hidden=True)(create_links_export.main_from_parser)
    app.command("collect", no_args_is_help=False, help=f"🧺 <c> {COLLECT_HELP}")(collect_dotfiles)
    app.command("c", no_args_is_help=False, help=COLLECT_HELP, hidden=True)(collect_dotfiles)
    app.command("register", no_args_is_help=True, help="📇 <r> Copy or symlink a dotfile into managed storage and register its mapping.")(register_dotfile)
    app.command("r", no_args_is_help=True, help="Copy or symlink a dotfile into managed storage and register its mapping.", hidden=True)(register_dotfile)
    app.command("export", no_args_is_help=False, help="📤 <e> Export dotfiles for migration to a new machine.")(export_dotfiles)
    app.command("e", no_args_is_help=False, help="Export dotfiles.", hidden=True)(export_dotfiles)
    app.command("import", no_args_is_help=False, help="📥 <i> Import dotfiles from an exported archive.")(import_dotfiles)
    app.command("i", no_args_is_help=False, help="Import dotfiles.", hidden=True)(import_dotfiles)
    register_managed_file_commands(app=app, kind="dotfiles", path_alias="p", init_alias="I", validate_alias="v")
    return app
