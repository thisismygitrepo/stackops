import json
import re
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


def yaml_schema_document_text(*, content: str, schema_reference: str) -> str:
    content = re.sub(r"(?m)^# yaml-language-server: \$schema=.*\n?", "", content)
    return f"""# yaml-language-server: $schema={schema_reference}
{content}"""


def ensure_yaml_schema_exists(*, yaml_path: Path, schema: JsonObject, schema_label: str) -> bool:
    schema_path = stackops_yaml_schema_path(yaml_path=yaml_path)
    existed = schema_path.exists()
    if existed and not schema_path.is_file():
        raise ValueError(f"{schema_label} schema path exists but is not a file: {schema_path}")

    schema_content = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    if not existed or schema_path.read_text(encoding="utf-8") != schema_content:
        schema_path.write_text(schema_content, encoding="utf-8")
    if yaml_path.is_file():
        content = yaml_path.read_text(encoding="utf-8")
        updated_content = yaml_schema_document_text(content=content, schema_reference=f"""./{schema_path.name}""")
        if content != updated_content:
            yaml_path.write_text(updated_content, encoding="utf-8")
    return not existed
