

import importlib.resources

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline as cline_package


def test_cline_package_ships_cline_privacy_module() -> None:
    assert importlib.resources.files(cline_package).joinpath("cline_privacy.py").is_file()
