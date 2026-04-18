from __future__ import annotations

import importlib.resources

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor as cursor_package


def test_cursor_package_ships_cursor_privacy_module() -> None:
    assert importlib.resources.files(cursor_package).joinpath("cursor_privacy.py").is_file()
