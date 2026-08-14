from pathlib import Path
from types import ModuleType
from typing import Annotated

import typer


DATA_SETUP_HELP = "Interactively add a backup entry and install its YAML schema."
DOTFILES_SETUP_HELP = "Interactively register a dotfile and install its YAML schema."
LAYOUTS_SETUP_HELP = "Install starter terminal layouts and their JSON schema."
SECRETS_SETUP_HELP = "Interactively create the global secrets file and schema."


def _ensure_packaged_schema(*, module: ModuleType, path_reference: str, schema_path: Path) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import exit_with_setup_error
    from stackops.utils.path_reference import get_path_reference_path

    if schema_path.exists():
        if not schema_path.is_file():
            exit_with_setup_error(f"Schema path exists but is not a file: {schema_path}")
        typer.echo(f"Schema already present: {schema_path}")
        return
    source_path = get_path_reference_path(module=module, path_reference=path_reference)
    try:
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError as exc:
        exit_with_setup_error(f"Could not install schema at {schema_path}: {exc}")
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Wrote {schema_path}")


def setup_data() -> None:
    import stackops.utils.schemas.mapper as mapper_assets
    from stackops.profile.dotfiles_mapper import DEFAULT_OS_FILTER
    from stackops.scripts.python.helpers.helpers_cloud.backup_config import USER_BACKUP_PATH
    from stackops.scripts.python.helpers.helpers_devops.cli_data import register_data

    _ensure_packaged_schema(
        module=mapper_assets,
        path_reference=mapper_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE,
        schema_path=USER_BACKUP_PATH.with_name(mapper_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE),
    )
    register_data(
        path_local=None,
        group="default",
        name=None,
        path_cloud=None,
        share_url=None,
        zip_=True,
        encryption=None,
        pwd=None,
        rel2home=None,
        os=DEFAULT_OS_FILTER,
        interactive=True,
    )


def setup_dotfiles() -> None:
    import stackops.utils.schemas.mapper as mapper_assets
    from stackops.profile.dotfiles_mapper import DEFAULT_OS_FILTER, USER_MAPPER_PATH
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import register_dotfile

    _ensure_packaged_schema(
        module=mapper_assets,
        path_reference=mapper_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE,
        schema_path=USER_MAPPER_PATH.with_name(mapper_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE),
    )
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
        record=True,
        interactive=True,
    )


def setup_layouts(
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing layouts and schema.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config import dump_config
    from stackops.utils.source_of_truth import DOTFILES_LAYOUTS_JSON_PATH

    dump_config(which="layout", data=False, schema=False, default_path=True, force=force, run=False)
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
    from stackops.utils.path_reference import get_path_reference_path

    secrets_exist = SECRETS_DOFILE.exists()
    if secrets_exist:
        if not SECRETS_DOFILE.is_file():
            exit_with_setup_error(f"Global secrets path exists but is not a file: {SECRETS_DOFILE}")
        try:
            load_secrets_file(SECRETS_DOFILE)
        except (OSError, SecretsSchemaError) as exc:
            exit_with_setup_error(f"Global secrets cannot be safely read:\n{exc}")

    schema_path = SECRETS_DOFILE.with_name(secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE)
    if schema_path.exists() and not schema_path.is_file():
        exit_with_setup_error(f"Secrets schema path exists but is not a file: {schema_path}")
    schema_content: str | None = None
    if not schema_path.exists():
        schema_source_path = get_path_reference_path(
            module=secrets_assets,
            path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE,
        )
        try:
            schema_content = schema_source_path.read_text(encoding="utf-8")
        except OSError as exc:
            exit_with_setup_error(f"Could not read the packaged secrets schema: {exc}")
    if secrets_exist:
        try:
            if schema_content is not None:
                schema_path.write_text(schema_content, encoding="utf-8")
        except OSError as exc:
            exit_with_setup_error(f"Could not install the global secrets schema: {exc}")
        typer.echo(
            f"Global secrets and schema are ready: {SECRETS_DOFILE}\n"
            "Add another login with:\n"
            "  devops config secrets add --source global"
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
        if schema_content is not None:
            schema_path.write_text(schema_content, encoding="utf-8")
    except OSError as exc:
        exit_with_setup_error(f"Global secrets setup was not completed: {exc}")
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Global secrets and schema are ready: {SECRETS_DOFILE}")
