from __future__ import annotations

import json

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.crush as crush_assets
from machineconfig.utils.path_reference import get_path_reference_path


def test_crush_path_reference_points_to_valid_json_asset() -> None:
    config_path = get_path_reference_path(module=crush_assets, path_reference=crush_assets.CRUSH_PATH_REFERENCE)
    config_data = json.loads(config_path.read_text(encoding="utf-8"))

    assert config_path.is_file()
    assert config_data["options"]["disable_metrics"] is True
    assert config_data["options"]["attribution"]["generated_with"] is False
