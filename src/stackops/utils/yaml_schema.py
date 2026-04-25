import json
from pathlib import Path
from typing import Final


type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

_SCHEMA_FILE_SUFFIX: Final[str] = ".schema.json"


def stackops_yaml_schema_path(*, yaml_path: Path) -> Path:
    return yaml_path.with_name(f"{yaml_path.stem}{_SCHEMA_FILE_SUFFIX}")


def yaml_language_server_schema_comment(*, yaml_path: Path) -> str:
    schema_path = stackops_yaml_schema_path(yaml_path=yaml_path)
    return f"# yaml-language-server: $schema=./{schema_path.name}"


def ensure_yaml_schema_exists(*, yaml_path: Path, schema: JsonObject, schema_label: str) -> bool:
    schema_path = stackops_yaml_schema_path(yaml_path=yaml_path)
    if schema_path.exists():
        if not schema_path.is_file():
            raise ValueError(f"{schema_label} schema path exists but is not a file: {schema_path}")
        return False

    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True
