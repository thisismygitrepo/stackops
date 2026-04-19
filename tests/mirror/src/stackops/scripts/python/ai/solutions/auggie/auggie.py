

from pathlib import Path

import pytest

from stackops.scripts.python.ai.solutions.auggie import auggie as auggie_module


def test_build_configuration_skips_output_when_instructions_disabled(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    auggie_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=False)

    assert (repo_root / ".augment").exists() is False


def test_build_configuration_writes_guidelines_from_instruction_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("auggie rules\n", encoding="utf-8")

    monkeypatch.setattr(auggie_module, "get_generic_instructions_path", lambda: instructions_path)

    auggie_module.build_configuration(repo_root=repo_root, add_private_config=False, add_instructions=True)

    assert (repo_root / ".augment" / "guidelines.md").read_text(encoding="utf-8") == "auggie rules\n"
