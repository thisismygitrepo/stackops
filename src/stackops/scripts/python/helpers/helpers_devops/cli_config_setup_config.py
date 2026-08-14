import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from stat import S_IMODE
from typing import Never

import typer

from stackops.utils.schemas.config.config_types import StackOpsConfig, StackOpsConfigStringKey


def exit_with_setup_error(message: str) -> Never:
    styled_message = typer.style("Error: ", fg=typer.colors.RED) + message
    typer.echo(styled_message, err=True)
    raise typer.Exit(code=1)


def load_stackops_config_for_setup(config_path: Path) -> StackOpsConfig | None:
    from stackops.utils.source_of_truth import read_stackops_config

    if not config_path.exists():
        return None
    if not config_path.is_file():
        exit_with_setup_error(f"StackOps config path exists but is not a file: {config_path}")
    try:
        return read_stackops_config()
    except (OSError, ValueError) as exc:
        exit_with_setup_error(
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


def write_stackops_config(
    *,
    config_path: Path,
    schema_path: Path,
    existing_config: StackOpsConfig | None,
    values: Mapping[StackOpsConfigStringKey, str],
) -> None:
    import stackops.utils.schemas.config as config_assets
    from stackops.utils.path_reference import get_path_reference_path
    from stackops.utils.schemas.config.constants import STACKOPS_CONFIG_FILE_MODE, STACKOPS_CONFIG_VERSION

    if schema_path.exists() and not schema_path.is_file():
        exit_with_setup_error(f"StackOps schema path exists but is not a file: {schema_path}")

    if existing_config is None:
        updated_config: StackOpsConfig = {
            "$schema": f"./{schema_path.name}",
            "version": STACKOPS_CONFIG_VERSION,
        }
        config_mode = STACKOPS_CONFIG_FILE_MODE
    else:
        updated_config = existing_config.copy()
        updated_config["$schema"] = f"./{schema_path.name}"
        config_mode = S_IMODE(config_path.stat().st_mode)

    for key, value in values.items():
        match key:
            case "default_rclone_config":
                updated_config["default_rclone_config"] = value
            case "default_email_config":
                updated_config["default_email_config"] = value
            case "default_email_address":
                updated_config["default_email_address"] = value

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
