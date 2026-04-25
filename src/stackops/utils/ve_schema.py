from pathlib import Path
from typing import Final

from stackops.utils.yaml_schema import JsonObject, ensure_yaml_schema_exists, yaml_language_server_schema_comment


_JSON_SCHEMA_DRAFT: Final[str] = "http://json-schema.org/draft-07/schema#"


def ve_yaml_header_for_path(*, yaml_path: Path) -> str:
    return f"""{yaml_language_server_schema_comment(yaml_path=yaml_path)}
# Virtual Environment Configuration File
# This file configures the virtual environment and cloud sync settings for this project
"""


def ensure_ve_yaml_schema_exists(*, yaml_path: Path) -> bool:
    return ensure_yaml_schema_exists(yaml_path=yaml_path, schema=_ve_yaml_schema(), schema_label="StackOps .ve.yaml")


def _ve_yaml_schema() -> JsonObject:
    return {
        "$schema": _JSON_SCHEMA_DRAFT,
        "title": "StackOps .ve.yaml",
        "description": "Project virtual environment and cloud sync defaults used by StackOps.",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "specs": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "ve_path": {
                        "type": "string",
                        "description": "Virtual environment directory path.",
                    },
                    "ipy_profile": _nullable_string_schema(description="Optional IPython profile name."),
                },
                "required": ["ve_path"],
            },
            "cloud": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "cloud": {
                        "type": "string",
                        "description": "Cloud storage identifier or rclone remote name.",
                    },
                    "root": {
                        "type": "string",
                        "description": "Root directory within the cloud storage.",
                    },
                    "rel2home": _boolean_schema(description="Whether local paths are relative to the home directory."),
                    "pwd": _nullable_string_schema(description="Optional password used for encryption."),
                    "key": _nullable_string_schema(description="Optional encryption key path."),
                    "encrypt": _boolean_schema(description="Whether cloud sync encrypts transferred files."),
                    "os_specific": _boolean_schema(description="Whether paths should be OS-specific."),
                    "zip": _boolean_schema(description="Whether files should be compressed before upload."),
                    "share": _boolean_schema(description="Whether sharing or public access is enabled."),
                    "overwrite": _boolean_schema(description="Whether existing files may be overwritten."),
                },
                "required": [
                    "cloud",
                    "root",
                    "rel2home",
                    "pwd",
                    "key",
                    "encrypt",
                    "os_specific",
                    "zip",
                    "share",
                    "overwrite",
                ],
            },
        },
        "anyOf": [{"required": ["specs"]}, {"required": ["cloud"]}],
    }


def _nullable_string_schema(*, description: str) -> JsonObject:
    return {"description": description, "type": ["string", "null"]}


def _boolean_schema(*, description: str) -> JsonObject:
    return {"description": description, "type": "boolean"}
