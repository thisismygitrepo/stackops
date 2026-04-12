from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

from machineconfig.scripts.python.ai.solutions.forge.forge import FORGE_SCHEMA_URL, build_configuration
from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


FORGE_MODULE = importlib.import_module("machineconfig.scripts.python.ai.solutions.forge.forge")
DEFAULT_FORGE_YAML = cast(Callable[[], str], getattr(FORGE_MODULE, "_default_forge_yaml"))
WRITE_JSON_IF_MISSING = cast(Callable[[Path, dict[str, object]], None], getattr(FORGE_MODULE, "_write_json_if_missing"))
WRITE_TEXT_IF_MISSING = cast(Callable[[Path, str], None], getattr(FORGE_MODULE, "_write_text_if_missing"))


def test_default_forge_yaml_contains_schema_url() -> None:
    assert (
        DEFAULT_FORGE_YAML()
        == f"""# yaml-language-server: $schema={FORGE_SCHEMA_URL}
"""
    )


def test_write_text_if_missing_creates_parent_and_preserves_existing_content(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("nested", "forge.yaml")

    WRITE_TEXT_IF_MISSING(target_path, "first\n")
    WRITE_TEXT_IF_MISSING(target_path, "second\n")

    assert target_path.read_text(encoding="utf-8") == "first\n"


def test_write_json_if_missing_creates_parent_and_preserves_existing_content(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("nested", ".mcp.json")

    WRITE_JSON_IF_MISSING(target_path, {"mcpServers": {}})
    WRITE_JSON_IF_MISSING(target_path, {"mcpServers": {"other": {}}})

    assert json.loads(target_path.read_text(encoding="utf-8")) == {"mcpServers": {}}


def test_build_configuration_writes_agents_and_private_files(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=True)

    assert tmp_path.joinpath("AGENTS.md").read_text(encoding="utf-8") == get_generic_instructions_path().read_text(encoding="utf-8")
    assert tmp_path.joinpath("forge.yaml").read_text(encoding="utf-8") == DEFAULT_FORGE_YAML()
    assert json.loads(tmp_path.joinpath(".mcp.json").read_text(encoding="utf-8")) == {"mcpServers": {}}


def test_build_configuration_does_not_overwrite_existing_private_files(tmp_path: Path) -> None:
    forge_yaml_path = tmp_path.joinpath("forge.yaml")
    mcp_json_path = tmp_path.joinpath(".mcp.json")
    forge_yaml_path.write_text("custom\n", encoding="utf-8")
    mcp_json_path.write_text('{"custom": true}\n', encoding="utf-8")

    build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=False)

    assert forge_yaml_path.read_text(encoding="utf-8") == "custom\n"
    assert mcp_json_path.read_text(encoding="utf-8") == '{"custom": true}\n'
    assert not tmp_path.joinpath("AGENTS.md").exists()
