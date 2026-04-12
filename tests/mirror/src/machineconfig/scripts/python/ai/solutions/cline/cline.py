from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.ai.solutions.cline import cline as cline_module


def test_build_configuration_skips_output_when_instructions_disabled(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    cline_module.build_configuration(
        repo_root=repo_root,
        add_private_config=True,
        add_instructions=False,
    )

    assert (repo_root / ".clinerules").exists() is False


def test_build_configuration_writes_cline_rules_from_instruction_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("cline rules\n", encoding="utf-8")

    monkeypatch.setattr(cline_module, "get_generic_instructions_path", lambda: instructions_path)

    cline_module.build_configuration(
        repo_root=repo_root,
        add_private_config=False,
        add_instructions=True,
    )

    assert (repo_root / ".clinerules" / "python_dev.md").read_text(encoding="utf-8") == "cline rules\n"
