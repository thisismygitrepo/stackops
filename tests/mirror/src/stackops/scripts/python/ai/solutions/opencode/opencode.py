from __future__ import annotations

from pathlib import Path

import stackops.scripts.python.ai.solutions.opencode as opencode_assets
from stackops.scripts.python.ai.solutions.opencode import opencode as opencode_module
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path
from stackops.utils.path_reference import get_path_reference_path


def test_build_configuration_writes_missing_opencode_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    opencode_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
    config_source = get_path_reference_path(module=opencode_assets, path_reference=opencode_assets.OPENCODE_PATH_REFERENCE).read_text(
        encoding="utf-8"
    )

    assert repo_root.joinpath("AGENTS.md").read_text(encoding="utf-8") == instructions_text
    assert repo_root.joinpath(".opencode/opencode.jsonc").read_text(encoding="utf-8") == config_source


def test_build_configuration_preserves_existing_agents_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    agents_path = repo_root.joinpath("AGENTS.md")
    agents_path.write_text(data="keep agents\n", encoding="utf-8")

    opencode_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    config_source = get_path_reference_path(module=opencode_assets, path_reference=opencode_assets.OPENCODE_PATH_REFERENCE).read_text(
        encoding="utf-8"
    )

    assert agents_path.read_text(encoding="utf-8") == "keep agents\n"
    assert repo_root.joinpath(".opencode/opencode.jsonc").read_text(encoding="utf-8") == config_source


def test_build_configuration_skips_opencode_files_when_unrequested(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    opencode_module.build_configuration(repo_root=repo_root, add_private_config=False, add_instructions=False)

    assert list(repo_root.iterdir()) == []
