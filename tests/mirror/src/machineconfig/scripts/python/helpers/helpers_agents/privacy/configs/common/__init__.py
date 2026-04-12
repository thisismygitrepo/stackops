from __future__ import annotations

import importlib.resources

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.common as common_package


def test_common_package_ships_privacy_orchestrator_module() -> None:
    assert importlib.resources.files(common_package).joinpath("privacy_orchestrator.py").is_file()
