from __future__ import annotations

from pathlib import Path

from machineconfig.scripts.python.ai.solutions.qwen_code import qwen_code as qwen_code_module
from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


def test_build_configuration_writes_qwen_markdown_when_requested(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    qwen_code_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")

    assert repo_root.joinpath("QWEN.md").read_text(encoding="utf-8") == instructions_text


def test_build_configuration_skips_qwen_files_when_instructions_disabled(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    qwen_code_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=False)

    assert list(repo_root.iterdir()) == []
