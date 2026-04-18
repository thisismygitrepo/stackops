import stackops.jobs.scripts.powershell_scripts as powershell_scripts
from stackops.utils.path_reference import get_path_reference_path


def test_powershell_script_reference_exists() -> None:
    script_path = get_path_reference_path(module=powershell_scripts, path_reference=powershell_scripts.CMATRIX_PATH_REFERENCE)

    assert script_path.is_file()
    assert script_path.suffix == ".ps1"
