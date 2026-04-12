from importlib.resources import files

import machineconfig.settings.shells.bash as bash_settings


def test_bash_path_reference_exists() -> None:
    assert (files(bash_settings) / bash_settings.INIT_PATH_REFERENCE).is_file()
