from typing import Annotated

import typer

from stackops.utils.managed_files import ManagedFileKind

DATA_SETUP_HELP = "Interactively add a backup entry and install its YAML schema."
DOTFILES_SETUP_HELP = "Interactively register a dotfile and install its YAML schema."
LAYOUTS_SETUP_HELP = "Install starter terminal layouts and their JSON schema."
SECRETS_SETUP_HELP = "Interactively create the global secrets file and schema."


def _ensure_user_schema(kind: ManagedFileKind) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import exit_with_setup_error
    from stackops.utils.managed_files import ensure_managed_schema, get_managed_file_spec

    spec = get_managed_file_spec(kind)
    try:
        written_path = ensure_managed_schema(spec=spec, data_path=spec.user_path)
    except OSError as exc:
        exit_with_setup_error(f"Could not install the {kind} schema next to {spec.user_path}: {exc}")
    if written_path is not None:
        typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Wrote {written_path}")


def setup_data() -> None:
    from stackops.profile.dotfiles_constants import DEFAULT_OS_FILTER
    from stackops.scripts.python.helpers.helpers_devops.cli_data import register_data

    _ensure_user_schema("data")
    register_data(
        path_local=None,
        group="default",
        name=None,
        path_cloud=None,
        share_url=None,
        no_zip=False,
        encryption=None,
        pwd=None,
        no_rel2home=False,
        os=DEFAULT_OS_FILTER,
        interactive=True,
    )


def setup_dotfiles() -> None:
    from stackops.profile.dotfiles_constants import DEFAULT_OS_FILTER
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import register_dotfile

    _ensure_user_schema("dotfiles")
    register_dotfile(
        file=None,
        method="copy",
        on_conflict="throw-error",
        sensitivity="private",
        destination=None,
        name=None,
        section="default",
        os_filter=DEFAULT_OS_FILTER,
        shared=False,
        no_record=False,
        interactive=True,
    )


def setup_layouts(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing layouts and schema.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dump import dump_config
    from stackops.utils.source_of_truth import DOTFILES_LAYOUTS_JSON_PATH

    dump_config(which="layouts", data=False, schema=False, default_path=True, force=force)
    typer.echo(f"Starter layouts are ready at {DOTFILES_LAYOUTS_JSON_PATH}")


def setup_secrets() -> None:
    import stackops.secrets.assets as secrets_assets
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_prompts import prompt_secret_login
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import exit_with_setup_error
    from stackops.secrets.constants import SECRETS_FILE_VERSION
    from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
    from stackops.secrets.models import SecretsFile
    from stackops.secrets.paths import SECRETS_DOFILE
    from stackops.secrets.writer import create_secrets_file

    if SECRETS_DOFILE.exists():
        if not SECRETS_DOFILE.is_file():
            exit_with_setup_error(f"Global secrets path exists but is not a file: {SECRETS_DOFILE}")
        try:
            load_secrets_file(SECRETS_DOFILE)
        except (OSError, SecretsSchemaError) as exc:
            exit_with_setup_error(f"Global secrets cannot be safely read:\n{exc}")
        _ensure_user_schema("secrets")
        typer.echo(
            f"Global secrets and schema are ready: {SECRETS_DOFILE}\n"
            "Add another login with:\n"
            "  devops vault secrets add --source global"
        )
        return

    typer.echo("Create the first global login entry. Secret values are hidden while you type.")
    secrets_file: SecretsFile = {
        "$schema": f"./{secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE}",
        "version": SECRETS_FILE_VERSION,
        "entries": [prompt_secret_login()],
    }
    try:
        create_secrets_file(secrets_path=SECRETS_DOFILE, secrets_file=secrets_file)
    except OSError as exc:
        exit_with_setup_error(f"Global secrets setup was not completed: {exc}")
    _ensure_user_schema("secrets")
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Global secrets and schema are ready: {SECRETS_DOFILE}")
