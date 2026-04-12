from __future__ import annotations

import platform
import tempfile
from pathlib import Path

import pytest

import machineconfig.scripts.python.ai.utils.shared as shared_module


def test_get_generic_instructions_path_adjusts_windows_terms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path.joinpath("dev.instructions.md")
    source_path.write_text("bash ./run.sh", encoding="utf-8")

    temp_dir = tmp_path.joinpath("temp")
    temp_dir.mkdir()

    def fake_get_path_reference_path(module: object, path_reference: str) -> Path:
        _ = module
        _ = path_reference
        return source_path

    monkeypatch.setattr(
        shared_module,
        "get_path_reference_path",
        fake_get_path_reference_path,
    )
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp_dir))

    result_path = shared_module.get_generic_instructions_path()

    assert result_path == temp_dir.joinpath("generic_instructions.md")
    assert result_path.read_text(encoding="utf-8") == "powershell ./run.ps1"


def test_get_generic_instructions_path_preserves_posix_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path.joinpath("dev.instructions.md")
    source_path.write_text("bash ./run.sh", encoding="utf-8")

    temp_dir = tmp_path.joinpath("temp")
    temp_dir.mkdir()

    def fake_get_path_reference_path(module: object, path_reference: str) -> Path:
        _ = module
        _ = path_reference
        return source_path

    monkeypatch.setattr(
        shared_module,
        "get_path_reference_path",
        fake_get_path_reference_path,
    )
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(temp_dir))

    result_path = shared_module.get_generic_instructions_path()

    assert result_path == temp_dir.joinpath("generic_instructions.md")
    assert result_path.read_text(encoding="utf-8") == "bash ./run.sh"
