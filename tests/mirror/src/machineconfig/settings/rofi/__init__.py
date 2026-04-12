from importlib.resources import files

import pytest

import machineconfig.settings.rofi as rofi_settings


@pytest.mark.parametrize(
    "path_reference",
    [
        rofi_settings.CONFIG_PATH_REFERENCE,
        rofi_settings.CONFIG_DEFAULT_PATH_REFERENCE,
    ],
)
def test_rofi_path_references_exist(path_reference: str) -> None:
    assert (files(rofi_settings) / path_reference).is_file()
