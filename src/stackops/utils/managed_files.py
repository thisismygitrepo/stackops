import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

ManagedFileKind: TypeAlias = Literal["config", "layouts", "dotfiles", "data", "secrets"]


@dataclass(frozen=True, slots=True)
class ManagedFileSpec:
    user_path: Path
    example_source_path: Path
    schema_source_path: Path
    initial_content: str
    file_mode: int


def get_managed_file_spec(kind: ManagedFileKind) -> ManagedFileSpec:
    from stackops.utils.path_reference import get_path_reference_path

    match kind:
        case "config":
            import stackops.utils.schemas.config as config_assets
            from stackops.utils.schemas.config.config_types import StackOpsConfig
            from stackops.utils.schemas.config.constants import STACKOPS_CONFIG_FILE_MODE, STACKOPS_CONFIG_VERSION
            from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH

            initial_config: StackOpsConfig = {"$schema": f"./{config_assets.CONFIG_SCHEMA_PATH_REFERENCE}", "version": STACKOPS_CONFIG_VERSION}
            return ManagedFileSpec(
                user_path=DOTFILES_STACKOPS_CONFIG_PATH,
                example_source_path=get_path_reference_path(module=config_assets, path_reference=config_assets.CONFIG_PATH_REFERENCE),
                schema_source_path=get_path_reference_path(module=config_assets, path_reference=config_assets.CONFIG_SCHEMA_PATH_REFERENCE),
                initial_content=json.dumps(initial_config, indent=2) + "\n",
                file_mode=STACKOPS_CONFIG_FILE_MODE,
            )
        case "layouts":
            import stackops.utils.schemas.layouts as layout_assets
            from stackops.utils.source_of_truth import DOTFILES_LAYOUTS_JSON_PATH

            layouts_example_path = get_path_reference_path(module=layout_assets, path_reference=layout_assets.LAYOUT_PATH_REFERENCE)
            return ManagedFileSpec(
                user_path=DOTFILES_LAYOUTS_JSON_PATH,
                example_source_path=layouts_example_path,
                schema_source_path=get_path_reference_path(module=layout_assets, path_reference=layout_assets.LAYOUT_SCHEMA_PATH_REFERENCE),
                initial_content=layouts_example_path.read_text(encoding="utf-8"),
                file_mode=0o644,
            )
        case "dotfiles":
            import stackops.utils.schemas.mapper as mapper_assets
            from stackops.profile.dotfiles_mapper import DEFAULT_DOTFILE_MAPPER_HEADER, dump_dotfiles_mapper
            from stackops.utils.source_of_truth import DOTFILES_USER_MAPPER_PATH

            return ManagedFileSpec(
                user_path=DOTFILES_USER_MAPPER_PATH,
                example_source_path=get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DOTFILES_PATH_REFERENCE),
                schema_source_path=get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE),
                initial_content=dump_dotfiles_mapper(mapper={}, header=DEFAULT_DOTFILE_MAPPER_HEADER),
                file_mode=0o644,
            )
        case "data":
            import stackops.utils.schemas.mapper as mapper_assets
            from stackops.scripts.python.helpers.helpers_cloud.backup_config import DEFAULT_BACKUP_HEADER
            from stackops.utils.source_of_truth import DOTFILES_USER_BACKUP_PATH

            return ManagedFileSpec(
                user_path=DOTFILES_USER_BACKUP_PATH,
                example_source_path=get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DATA_PATH_REFERENCE),
                schema_source_path=get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE),
                initial_content=DEFAULT_BACKUP_HEADER,
                file_mode=0o644,
            )
        case "secrets":
            import stackops.secrets.assets as secrets_assets
            from stackops.secrets.paths import SECRETS_DOFILE
            from stackops.secrets.writer import PRIVATE_SECRETS_FILE_MODE

            secrets_example_path = get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE)
            return ManagedFileSpec(
                user_path=SECRETS_DOFILE,
                example_source_path=secrets_example_path,
                schema_source_path=get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE),
                initial_content=secrets_example_path.read_text(encoding="utf-8"),
                file_mode=PRIVATE_SECRETS_FILE_MODE,
            )


def managed_schema_path(*, spec: ManagedFileSpec, data_path: Path) -> Path:
    return data_path.with_name(spec.schema_source_path.name)


def ensure_managed_schema(*, spec: ManagedFileSpec, data_path: Path) -> Path | None:
    schema_path = managed_schema_path(spec=spec, data_path=data_path)
    if schema_path.exists():
        if not schema_path.is_file():
            raise IsADirectoryError(f"Schema path exists but is not a file: {schema_path}")
        return None
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(spec.schema_source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return schema_path
