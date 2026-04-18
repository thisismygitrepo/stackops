from __future__ import annotations

import stackops.scripts.python.ai.solutions.kilocode as kilocode_assets
from stackops.utils.path_reference import get_path_reference_path


def test_kilocode_privacy_path_reference_resolves_to_existing_asset() -> None:
    privacy_path = get_path_reference_path(module=kilocode_assets, path_reference=kilocode_assets.PRIVACY_PATH_REFERENCE)

    assert privacy_path.is_file()
    assert privacy_path.name == kilocode_assets.PRIVACY_PATH_REFERENCE
    assert privacy_path.read_text(encoding="utf-8").strip() != ""
