from __future__ import annotations

import importlib.resources

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex as codex_package


def test_codex_package_ships_codex_privacy_module() -> None:
    assert importlib.resources.files(codex_package).joinpath("codex_privacy.py").is_file()
