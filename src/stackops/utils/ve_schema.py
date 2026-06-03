from pathlib import Path
from typing import cast

import stackops.utils.schemas.ve as ve_schema_assets
from stackops.utils.files.read import read_json
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.yaml_schema import JsonObject, ensure_yaml_schema_exists, yaml_language_server_schema_comment


def ve_yaml_header_for_path(*, yaml_path: Path) -> str:
    return f"""{yaml_language_server_schema_comment(yaml_path=yaml_path)}
# Virtual Environment Configuration File
# This file configures the virtual environment and cloud sync settings for this project
"""


def ensure_ve_yaml_schema_exists(*, yaml_path: Path) -> bool:
    return ensure_yaml_schema_exists(yaml_path=yaml_path, schema=_ve_yaml_schema(), schema_label="StackOps .ve.yaml")


def _ve_yaml_schema() -> JsonObject:
    schema_path = get_path_reference_path(
        module=ve_schema_assets,
        path_reference=ve_schema_assets.VE_SCHEMA_PATH_REFERENCE,
    )
    return cast(JsonObject, read_json(schema_path))
