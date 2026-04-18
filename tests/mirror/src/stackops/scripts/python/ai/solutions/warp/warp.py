from __future__ import annotations

from pathlib import Path

import pytest

import stackops.scripts.python.ai.solutions.warp.warp as warp_module


def test_build_configuration_skips_instruction_file_when_disabled(tmp_path: Path) -> None:
    warp_module.build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=False)

    assert not tmp_path.joinpath("WARP.md").exists()


def test_build_configuration_writes_generic_instructions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    instructions_path = tmp_path.joinpath("instructions.md")
    instructions_path.write_text("warp instructions", encoding="utf-8")

    def fake_get_generic_instructions_path() -> Path:
        return instructions_path

    monkeypatch.setattr(warp_module, "get_generic_instructions_path", fake_get_generic_instructions_path)

    warp_module.build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=True)

    assert tmp_path.joinpath("WARP.md").read_text(encoding="utf-8") == "warp instructions"
