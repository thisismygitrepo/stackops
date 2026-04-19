

from stackops.scripts import windows as module


def test_wrap_stackops_path_reference_points_to_powershell_wrapper() -> None:
    assert module.WRAP_STACKOPS_PATH_REFERENCE == "wrap_stackops.ps1"
    assert module.WRAP_STACKOPS_PATH_REFERENCE.endswith(".ps1")
