from pathlib import Path

from stackops.utils.schemas.config.constants import LEGACY_STACKOPS_CONFIG_FILE_NAME, STACKOPS_CONFIG_VERSION


def migrate_stackops_config_json_to_yaml(config_path: Path) -> None:
    legacy_path = config_path.with_name(LEGACY_STACKOPS_CONFIG_FILE_NAME)
    if not legacy_path.is_file() or config_path.exists():
        return

    import json
    from stat import S_IMODE
    from typing import cast

    from rich.console import Console
    from rich.panel import Panel

    from stackops.utils.managed_files import ensure_managed_schema, get_managed_file_spec
    from stackops.utils.schemas.yaml_document import yaml_document_text
    from stackops.utils.schemas.yaml_schema import yaml_language_server_schema_comment

    try:
        legacy_document: object = json.loads(legacy_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"""StackOps config migration to YAML failed: invalid JSON in {legacy_path}: {error}""") from error
    if not isinstance(legacy_document, dict):
        raise ValueError(f"""StackOps config migration to YAML failed: {legacy_path} must hold a JSON object.""")
    legacy_values = {key: value for key, value in cast(dict[str, object], legacy_document).items() if key not in ("$schema", "version")}
    with config_path.open("x", encoding="utf-8") as stream:
        config_path.chmod(S_IMODE(legacy_path.stat().st_mode))
        stream.write(
            f"""{yaml_language_server_schema_comment(yaml_path=config_path)}
{yaml_document_text(document={"version": STACKOPS_CONFIG_VERSION, **legacy_values})}"""
        )
    ensure_managed_schema(spec=get_managed_file_spec("config"), data_path=config_path)
    backup_path = legacy_path.with_name(f"""{legacy_path.name}.before_stackops_yaml_migration""")
    legacy_path.replace(backup_path)
    Console(stderr=True).print(
        Panel(
            f"""🔁 MIGRATION | The StackOps config is now a YAML file.
Converted `{legacy_path}` to `{config_path}`.
Backup of the previous file: `{backup_path}`""",
            title="[bold yellow]StackOps Config Migration[/bold yellow]",
            border_style="yellow",
        )
    )
