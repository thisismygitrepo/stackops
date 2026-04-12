from importlib.resources import files

import pytest

import machineconfig.settings.shells.alacritty as alacritty_settings


@pytest.mark.parametrize("path_reference", [alacritty_settings.ALACRITTY_TOML_PATH_REFERENCE, alacritty_settings.ALACRITTY_YML_PATH_REFERENCE])
def test_alacritty_path_references_exist(path_reference: str) -> None:
    assert (files(alacritty_settings) / path_reference).is_file()
