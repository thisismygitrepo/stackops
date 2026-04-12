from __future__ import annotations

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.copilot as copilot_assets
from machineconfig.utils.path_reference import get_path_reference_path


def test_copilot_path_reference_points_to_packaged_config() -> None:
    config_path = get_path_reference_path(module=copilot_assets, path_reference=copilot_assets.CONFIG_PATH_REFERENCE)

    assert config_path.is_file()
    assert "optional_usage_analytics: false" in config_path.read_text(encoding="utf-8")
