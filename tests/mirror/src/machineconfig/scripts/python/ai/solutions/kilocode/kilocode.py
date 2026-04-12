from __future__ import annotations

import json
from pathlib import Path

import machineconfig.scripts.python.ai.solutions.kilocode as kilocode_assets
from machineconfig.scripts.python.ai.solutions.kilocode import kilocode as kilocode_module
from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path
from machineconfig.utils.path_reference import get_path_reference_path


def expected_kilocodeignore() -> str:
    return "# Secrets and credentials\n.env\n.env.*\nsecrets/\n**/*.pem\n**/*.key\n**/credentials*.json\n!*.env.example\n"


def test_build_configuration_writes_missing_kilocode_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    kilocode_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
    privacy_source = get_path_reference_path(module=kilocode_assets, path_reference=kilocode_assets.PRIVACY_PATH_REFERENCE).read_text(
        encoding="utf-8"
    )

    assert repo_root.joinpath(".kilocode/rules/rules.md").read_text(encoding="utf-8") == instructions_text
    assert repo_root.joinpath("AGENTS.md").read_text(encoding="utf-8") == instructions_text
    mcp_config: object = json.loads(repo_root.joinpath(".kilocode/mcp.json").read_text(encoding="utf-8"))
    assert mcp_config == {"mcpServers": {}}
    assert repo_root.joinpath(".kilocodeignore").read_text(encoding="utf-8") == expected_kilocodeignore()
    assert repo_root.joinpath(".kilocode/rules/privacy.md").read_text(encoding="utf-8") == privacy_source


def test_build_configuration_preserves_existing_kilocode_optional_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    agents_path = repo_root.joinpath("AGENTS.md")
    agents_path.write_text(data="keep agents\n", encoding="utf-8")

    mcp_path = repo_root.joinpath(".kilocode/mcp.json")
    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    mcp_path.write_text(data='{"keep": true}\n', encoding="utf-8")

    ignore_path = repo_root.joinpath(".kilocodeignore")
    ignore_path.write_text(data="keep ignore\n", encoding="utf-8")

    privacy_path = repo_root.joinpath(".kilocode/rules/privacy.md")
    privacy_path.parent.mkdir(parents=True, exist_ok=True)
    privacy_path.write_text(data="keep privacy\n", encoding="utf-8")

    kilocode_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")

    assert repo_root.joinpath(".kilocode/rules/rules.md").read_text(encoding="utf-8") == instructions_text
    assert agents_path.read_text(encoding="utf-8") == "keep agents\n"
    assert mcp_path.read_text(encoding="utf-8") == '{"keep": true}\n'
    assert ignore_path.read_text(encoding="utf-8") == "keep ignore\n"
    assert privacy_path.read_text(encoding="utf-8") == "keep privacy\n"
