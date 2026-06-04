import json
from pathlib import Path
from typing import Any

import stackops.utils.schemas.agents as agents_schema_assets
import stackops.utils.schemas.config as config_schema_assets
import stackops.utils.schemas.ve as ve_schema_assets
from stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas import ensure_stackops_yaml_schema_exists
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.ve_schema import ensure_ve_yaml_schema_exists


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_agent_yaml_schemas_are_loaded_from_schema_assets(tmp_path: Path) -> None:
    prompts_yaml_path = tmp_path / "prompts.yaml"
    parallel_yaml_path = tmp_path / "parallel.yaml"

    assert ensure_stackops_yaml_schema_exists(yaml_path=prompts_yaml_path, schema_kind="prompts") is True
    assert ensure_stackops_yaml_schema_exists(yaml_path=parallel_yaml_path, schema_kind="parallel") is True

    expected_prompts_schema_path = get_path_reference_path(
        module=agents_schema_assets, path_reference=agents_schema_assets.PROMPTS_YAML_SCHEMA_PATH_REFERENCE
    )
    expected_parallel_schema_path = get_path_reference_path(
        module=agents_schema_assets, path_reference=agents_schema_assets.PARALLEL_YAML_SCHEMA_PATH_REFERENCE
    )

    assert _read_json(tmp_path / "prompts.schema.json") == _read_json(expected_prompts_schema_path)
    assert _read_json(tmp_path / "parallel.schema.json") == _read_json(expected_parallel_schema_path)


def test_ve_yaml_schema_is_loaded_from_schema_asset(tmp_path: Path) -> None:
    ve_yaml_path = tmp_path / ".ve.yaml"

    assert ensure_ve_yaml_schema_exists(yaml_path=ve_yaml_path) is True

    expected_schema_path = get_path_reference_path(module=ve_schema_assets, path_reference=ve_schema_assets.VE_SCHEMA_PATH_REFERENCE)

    assert _read_json(tmp_path / ".ve.schema.json") == _read_json(expected_schema_path)


def test_stackops_config_schema_asset_is_valid_json() -> None:
    schema_path = get_path_reference_path(module=config_schema_assets, path_reference=config_schema_assets.CONFIG_SCHEMA_PATH_REFERENCE)

    schema = _read_json(schema_path)

    assert schema["title"] == "StackOps User Config Schema"
    assert "general" not in schema["properties"]
    assert "repos" not in schema["properties"]
    assert schema["required"] == ["version"]
