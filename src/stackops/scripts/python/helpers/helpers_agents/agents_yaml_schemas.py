from pathlib import Path
from typing import Final, Literal, get_args

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER, ReasoningEffort
from stackops.utils.yaml_schema import JsonObject, JsonValue, ensure_yaml_schema_exists


type StackopsYamlSchemaKind = Literal["prompts", "parallel"]

PARALLEL_CREATE_CONFIG_KEYS: Final[frozenset[str]] = frozenset(
    {
        "agent",
        "model",
        "reasoning_effort",
        "provider",
        "host",
        "context",
        "context_path",
        "separator",
        "agent_load",
        "prompt",
        "prompt_path",
        "prompt_name",
        "job_name",
        "join_prompt_and_context",
        "output_path",
        "agents_dir",
        "interactive",
    }
)

_JSON_SCHEMA_DRAFT: Final[str] = "http://json-schema.org/draft-07/schema#"


def ensure_stackops_yaml_schema_exists(*, yaml_path: Path, schema_kind: StackopsYamlSchemaKind) -> bool:
    schema = _stackops_yaml_schema(schema_kind=schema_kind)
    return ensure_yaml_schema_exists(yaml_path=yaml_path, schema=schema, schema_label=f"StackOps {schema_kind} YAML")


def _stackops_yaml_schema(*, schema_kind: StackopsYamlSchemaKind) -> JsonObject:
    match schema_kind:
        case "prompts":
            return _prompts_yaml_schema()
        case "parallel":
            return _parallel_yaml_schema()


def _prompts_yaml_schema() -> JsonObject:
    return {
        "$schema": _JSON_SCHEMA_DRAFT,
        "title": "StackOps prompts.yaml",
        "description": "Named prompt and context entries used by `agents run`.",
        "type": "object",
        "additionalProperties": {"$ref": "#/definitions/promptEntry"},
        "definitions": {
            "promptEntry": {
                "description": "Prompt text, a prompt object, or a nested namespace of prompt entries.",
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {
                            "description": _nullable_string_schema(
                                description="Human-facing description. Ignored when StackOps builds prompt text."
                            ),
                            "desc": _nullable_string_schema(
                                description="Short human-facing description. Ignored when StackOps builds prompt text."
                            ),
                            "desciption": _nullable_string_schema(
                                description="Legacy misspelling accepted by StackOps and ignored when building prompt text."
                            ),
                            "agent": _enum_or_null_schema(
                                values=_literal_values(raw_values=get_args(AGENTS)),
                                description="Optional preferred agent label. Ignored when StackOps builds prompt text.",
                            ),
                            "prompt": _nullable_string_schema(description="Prompt or context text."),
                            "directory": _nullable_string_schema(description="Working directory displayed with this prompt."),
                        },
                        "additionalProperties": {"$ref": "#/definitions/promptEntry"},
                    },
                ],
            }
        },
    }


def _parallel_yaml_schema() -> JsonObject:
    return {
        "$schema": _JSON_SCHEMA_DRAFT,
        "title": "StackOps parallel.yaml",
        "description": "Named parallel agent workflow entries used by `agents parallel run-parallel`.",
        "type": "object",
        "additionalProperties": {"$ref": "#/definitions/parallelNode"},
        "definitions": {
            "parallelNode": {
                "oneOf": [
                    {"$ref": "#/definitions/runEntry"},
                    {"$ref": "#/definitions/runGroup"},
                ]
            },
            "runGroup": {
                "type": "object",
                "propertyNames": {"not": {"enum": _sorted_config_key_values()}},
                "additionalProperties": {"$ref": "#/definitions/parallelNode"},
            },
            "runEntry": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": False,
                "properties": {
                    "agent": _enum_or_null_schema(
                        values=_literal_values(raw_values=get_args(AGENTS)),
                        description="Agent implementation passed to `agents parallel create`.",
                    ),
                    "model": _nullable_string_schema(description="Optional model name passed to the selected agent."),
                    "reasoning_effort": _enum_or_null_schema(
                        values=_literal_values(raw_values=get_args(ReasoningEffort)),
                        description="Optional reasoning effort passed to agents that support it.",
                    ),
                    "provider": _enum_or_null_schema(
                        values=_literal_values(raw_values=get_args(PROVIDER)),
                        description="Optional provider passed to agents that support it.",
                    ),
                    "host": _enum_or_null_schema(
                        values=_literal_values(raw_values=get_args(HOST)),
                        description="Execution host for generated agent commands.",
                    ),
                    "context": _nullable_string_schema(description="Inline context shared with generated agent prompts."),
                    "context_path": _nullable_string_schema(description="Path to a context file."),
                    "separator": _nullable_string_schema(description="Escaped separator used to split context chunks."),
                    "agent_load": {
                        "description": "Number of parallel agents to generate.",
                        "type": ["integer", "null"],
                        "minimum": 1,
                    },
                    "prompt": _nullable_string_schema(description="Inline prompt sent to each generated agent."),
                    "prompt_path": _nullable_string_schema(description="Path to a prompt file."),
                    "prompt_name": _nullable_string_schema(description="Named prompt from prompts.yaml."),
                    "job_name": _nullable_string_schema(description="Name of the generated agent job directory."),
                    "join_prompt_and_context": {
                        "description": "Whether to combine prompt and context before splitting work.",
                        "type": ["boolean", "null"],
                    },
                    "output_path": _nullable_string_schema(description="Path where generated layout JSON is written."),
                    "agents_dir": _nullable_string_schema(description="Directory where generated agent files are written."),
                    "interactive": {
                        "description": "Whether to run the interactive create flow after resolving this entry.",
                        "type": ["boolean", "null"],
                    },
                },
            },
        },
    }


def _nullable_string_schema(*, description: str) -> JsonObject:
    return {"description": description, "type": ["string", "null"]}


def _enum_or_null_schema(*, values: list[str], description: str) -> JsonObject:
    enum_values: list[JsonValue] = [*values, None]
    return {"description": description, "enum": enum_values}


def _literal_values(*, raw_values: tuple[object, ...]) -> list[str]:
    values: list[str] = []
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            raise TypeError(f"Expected Literal value to be a string, got: {raw_value!r}")
        values.append(raw_value)
    return values


def _sorted_config_key_values() -> list[JsonValue]:
    values: list[JsonValue] = []
    for key in sorted(PARALLEL_CREATE_CONFIG_KEYS):
        values.append(key)
    return values
