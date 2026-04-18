import pytest

import stackops.jobs.scripts.bash_scripts as bash_scripts
from stackops.utils.path_reference import get_path_reference_path


@pytest.mark.parametrize("path_reference", [bash_scripts.HOLLYWOOD_PATH_REFERENCE, bash_scripts.LID_PATH_REFERENCE])
def test_bash_script_reference_exists(path_reference: str) -> None:
    script_path = get_path_reference_path(module=bash_scripts, path_reference=path_reference)

    assert script_path.is_file()
    assert script_path.suffix == ".sh"
