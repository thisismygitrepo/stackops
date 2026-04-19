

import json

import stackops.scripts.python.ai.solutions.crush as crush_assets
from stackops.utils.path_reference import get_path_reference_path


def test_path_references_resolve_to_existing_crush_assets() -> None:
    crush_config_path = get_path_reference_path(module=crush_assets, path_reference=crush_assets.CRUSH_PATH_REFERENCE)
    privacy_path = get_path_reference_path(module=crush_assets, path_reference=crush_assets.PRIVACY_PATH_REFERENCE)

    crush_config = json.loads(crush_config_path.read_text(encoding="utf-8"))

    assert crush_config_path.name == "crush.json"
    assert crush_config_path.is_file()
    assert isinstance(crush_config, dict)
    assert crush_config["$schema"] == "https://charm.land/crush.json"
    assert "providers" in crush_config
    assert privacy_path.name == "privacy.md"
    assert privacy_path.is_file()
    assert privacy_path.read_text(encoding="utf-8") != ""
