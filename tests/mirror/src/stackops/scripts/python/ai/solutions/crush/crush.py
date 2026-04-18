from __future__ import annotations

from pathlib import Path

from stackops.scripts.python.ai.solutions.crush.crush import build_configuration
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def test_build_configuration_writes_crush_markdown_when_instructions_enabled(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=True)

    assert tmp_path.joinpath("CRUSH.md").read_text(encoding="utf-8") == get_generic_instructions_path().read_text(encoding="utf-8")


def test_build_configuration_does_not_create_private_crush_files(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=False)

    assert not tmp_path.joinpath(".crush.json").exists()
    assert not tmp_path.joinpath(".crushignore").exists()
    assert not tmp_path.joinpath("CRUSH.md").exists()
