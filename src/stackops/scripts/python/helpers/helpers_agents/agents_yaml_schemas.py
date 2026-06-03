from pathlib import Path
from typing import Final, Literal, cast

import stackops.utils.schemas.agents as agents_schema_assets
from stackops.utils.files.read import read_json
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.yaml_schema import JsonObject, ensure_yaml_schema_exists


type StackopsYamlSchemaKind = Literal["prompts", "parallel"]

_SCHEMA_PATH_REFERENCES: Final[dict[StackopsYamlSchemaKind, str]] = {
    "prompts": agents_schema_assets.PROMPTS_YAML_SCHEMA_PATH_REFERENCE,
    "parallel": agents_schema_assets.PARALLEL_YAML_SCHEMA_PATH_REFERENCE,
}


def ensure_stackops_yaml_schema_exists(*, yaml_path: Path, schema_kind: StackopsYamlSchemaKind) -> bool:
    schema = _stackops_yaml_schema(schema_kind=schema_kind)
    return ensure_yaml_schema_exists(yaml_path=yaml_path, schema=schema, schema_label=f"StackOps {schema_kind} YAML")


def _stackops_yaml_schema(*, schema_kind: StackopsYamlSchemaKind) -> JsonObject:
    schema_path = get_path_reference_path(
        module=agents_schema_assets,
        path_reference=_SCHEMA_PATH_REFERENCES[schema_kind],
    )
    return cast(JsonObject, read_json(schema_path))
