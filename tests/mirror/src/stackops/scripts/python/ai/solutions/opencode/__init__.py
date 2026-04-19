

import stackops.scripts.python.ai.solutions.opencode as opencode_assets
from stackops.utils.path_reference import get_path_reference_path


def test_opencode_path_reference_resolves_to_existing_asset() -> None:
    config_path = get_path_reference_path(module=opencode_assets, path_reference=opencode_assets.OPENCODE_PATH_REFERENCE)

    assert config_path.is_file()
    assert config_path.name == opencode_assets.OPENCODE_PATH_REFERENCE
    assert config_path.read_text(encoding="utf-8").strip() != ""
