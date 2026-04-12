from importlib.resources import files

import pytest

import machineconfig.settings.mprocs.windows as windows_settings


@pytest.mark.parametrize(
    "path_reference",
    [
        windows_settings.MPROCS_PATH_REFERENCE,
        windows_settings.OTHER_PATH_REFERENCE,
    ],
)
def test_windows_path_references_exist(path_reference: str) -> None:
    assert (files(windows_settings) / path_reference).is_file()
