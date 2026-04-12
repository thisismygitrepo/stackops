from __future__ import annotations

import json

import machineconfig.scripts.python.ai.solutions.gemini as gemini_assets
from machineconfig.utils.path_reference import get_path_reference_path


def test_gemini_path_references_resolve_to_existing_assets() -> None:
    instructions_path = get_path_reference_path(module=gemini_assets, path_reference=gemini_assets.INSTRUCTIONS_PATH_REFERENCE)
    settings_path = get_path_reference_path(module=gemini_assets, path_reference=gemini_assets.SETTINGS_PATH_REFERENCE)

    assert instructions_path.is_file()
    assert instructions_path.name == gemini_assets.INSTRUCTIONS_PATH_REFERENCE
    assert instructions_path.read_text(encoding="utf-8").strip() != ""

    assert settings_path.is_file()
    assert settings_path.name == gemini_assets.SETTINGS_PATH_REFERENCE
    parsed_settings: object = json.loads(settings_path.read_text(encoding="utf-8"))
    assert isinstance(parsed_settings, dict)
