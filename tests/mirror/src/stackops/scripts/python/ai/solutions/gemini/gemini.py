from __future__ import annotations

from pathlib import Path

import stackops.scripts.python.ai.solutions.gemini as gemini_assets
from stackops.scripts.python.ai.solutions.gemini import gemini as gemini_module
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path
from stackops.utils.path_reference import get_path_reference_path


def expected_gemini_instructions_text() -> str:
    generic_instructions = get_generic_instructions_path().read_text(encoding="utf-8").rstrip()
    gemini_instructions = (
        get_path_reference_path(module=gemini_assets, path_reference=gemini_assets.INSTRUCTIONS_PATH_REFERENCE).read_text(encoding="utf-8").rstrip()
    )
    return f"{generic_instructions}\n\n{gemini_instructions}\n"


def test_build_configuration_writes_only_gemini_instructions_when_requested(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    gemini_module.build_configuration(repo_root=repo_root, add_private_config=False, add_instructions=True)

    assert repo_root.joinpath("GEMINI.md").read_text(encoding="utf-8") == expected_gemini_instructions_text()
    assert repo_root.joinpath(".gemini").exists() is False


def test_build_configuration_writes_requested_gemini_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    gemini_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    settings_source_path = get_path_reference_path(module=gemini_assets, path_reference=gemini_assets.SETTINGS_PATH_REFERENCE)

    assert repo_root.joinpath("GEMINI.md").read_text(encoding="utf-8") == expected_gemini_instructions_text()
    assert repo_root.joinpath(".gemini/settings.json").read_text(encoding="utf-8") == settings_source_path.read_text(encoding="utf-8")


def test_build_configuration_skips_gemini_files_when_unrequested(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    gemini_module.build_configuration(repo_root=repo_root, add_private_config=False, add_instructions=False)

    assert list(repo_root.iterdir()) == []
