import json
import os
import tempfile
from pathlib import Path
from stat import S_IMODE
from typing import Annotated, Never

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stackops.utils.schemas.config.config_types import StackOpsConfig


CLOUD_SETUP_HELP = "Select an rclone remote and create or update the StackOps config and schema."


def _exit_with_error(message: str) -> Never:
    styled_message = typer.style("Error: ", fg=typer.colors.RED) + message
    typer.echo(styled_message, err=True)
    raise typer.Exit(code=1)


def _load_stackops_config(config_path: Path) -> StackOpsConfig | None:
    from stackops.utils.source_of_truth import read_stackops_config

    if not config_path.exists():
        return None
    if not config_path.is_file():
        _exit_with_error(f"StackOps config path exists but is not a file: {config_path}")
    try:
        return read_stackops_config()
    except (OSError, ValueError) as exc:
        _exit_with_error(
            f"StackOps config cannot be safely updated because it is invalid:\n{exc}\n\n"
            "Fix the file, or create a reference copy with:\n"
            "  devops config dump --which config"
        )


def _write_text_atomically(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.chmod(temporary_path, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)
        raise


def _select_remote(remote_names: tuple[str, ...], configured_remote: str | None) -> str:
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_choice

    default_remote = configured_remote if configured_remote in remote_names else remote_names[0]
    return ask_choice(
        "Default rclone remote",
        help_text=(
            "StackOps stores the name of an existing rclone remote here; credentials remain in rclone's own config. "
            "The name is saved without its trailing colon."
        ),
        choices=remote_names,
        default=default_remote,
    )


def setup_cloud(
    cloud: Annotated[
        str | None,
        typer.Option("--cloud", "-c", help="Use this existing rclone remote instead of prompting."),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Write without confirmation. Requires --cloud.")] = False,
) -> None:
    from stackops.utils.cloud.rclone import list_remote_names
    from stackops.utils.path_reference import get_path_reference_path
    from stackops.utils.schemas.config.constants import STACKOPS_CONFIG_FILE_MODE, STACKOPS_CONFIG_VERSION
    import stackops.utils.schemas.config as config_assets
    from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH

    if yes and cloud is None:
        _exit_with_error("--yes requires --cloud so the selected remote is explicit.")

    try:
        remote_names = list_remote_names()
    except RuntimeError as exc:
        _exit_with_error(
            f"Could not inspect rclone remotes:\n{exc}\n\n"
            "Create or repair an rclone remote with:\n"
            "  rclone config"
        )
    if len(remote_names) == 0:
        _exit_with_error(
            "No rclone remotes are configured. StackOps stores a remote name, not cloud credentials.\n\n"
            "Create a remote first:\n"
            "  rclone config\n\n"
            "Then rerun:\n"
            "  devops config setup cloud"
        )

    config_path = DOTFILES_STACKOPS_CONFIG_PATH
    schema_path = config_path.with_name(config_assets.CONFIG_SCHEMA_PATH_REFERENCE)
    if schema_path.exists() and not schema_path.is_file():
        _exit_with_error(f"StackOps schema path exists but is not a file: {schema_path}")

    existing_config = _load_stackops_config(config_path=config_path)
    configured_remote = existing_config.get("default_rclone_config") if existing_config is not None else None
    if cloud is None:
        selected_remote = _select_remote(remote_names=remote_names, configured_remote=configured_remote)
    else:
        selected_remote = cloud.strip()
        if selected_remote == "":
            _exit_with_error("--cloud must name an existing rclone remote.")
        if selected_remote.endswith(":"):
            _exit_with_error("Pass the rclone remote name without its trailing colon.")
        if selected_remote not in remote_names:
            _exit_with_error(
                f"Rclone remote {selected_remote!r} does not exist. Available remotes: {', '.join(remote_names)}\n\n"
                "Create another remote with:\n"
                "  rclone config"
            )

    if existing_config is None:
        updated_config: StackOpsConfig = {
            "$schema": f"./{config_assets.CONFIG_SCHEMA_PATH_REFERENCE}",
            "version": STACKOPS_CONFIG_VERSION,
            "default_rclone_config": selected_remote,
        }
        config_action = "Create"
        config_mode = STACKOPS_CONFIG_FILE_MODE
    else:
        updated_config: StackOpsConfig = existing_config.copy()
        updated_config["$schema"] = f"./{config_assets.CONFIG_SCHEMA_PATH_REFERENCE}"
        updated_config["default_rclone_config"] = selected_remote
        config_action = "Update"
        config_mode = S_IMODE(config_path.stat().st_mode)

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold cyan", no_wrap=True)
    summary.add_column(overflow="fold")
    summary.add_row("Action", config_action)
    summary.add_row("Rclone remote", selected_remote)
    summary.add_row("Config", config_path.as_posix())
    summary.add_row("Schema", schema_path.as_posix())
    console = Console()
    console.print(Panel(summary, title="Cloud Configuration", border_style="cyan", padding=(1, 2)))
    if not yes and not typer.confirm("Write this configuration?", default=True):
        raise typer.Exit(code=0)

    schema_source_path = get_path_reference_path(
        module=config_assets,
        path_reference=config_assets.CONFIG_SCHEMA_PATH_REFERENCE,
    )
    schema_mode = S_IMODE(schema_path.stat().st_mode) if schema_path.exists() else STACKOPS_CONFIG_FILE_MODE
    _write_text_atomically(
        path=schema_path,
        content=schema_source_path.read_text(encoding="utf-8"),
        mode=schema_mode,
    )
    config_content = json.dumps(updated_config, indent=2, ensure_ascii=False) + "\n"
    _write_text_atomically(path=config_path, content=config_content, mode=config_mode)
    console.print(
        Panel(
            f"Default cloud is now [bold]{selected_remote}[/bold].\n"
            "Commands that omit --cloud will use this rclone remote.",
            title="Configuration Saved",
            border_style="green",
            padding=(1, 2),
        )
    )


def get_app() -> typer.Typer:
    app = typer.Typer(
        help="Guided setup for StackOps configuration files.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    app.command("cloud", no_args_is_help=False, help=CLOUD_SETUP_HELP)(setup_cloud)
    return app
