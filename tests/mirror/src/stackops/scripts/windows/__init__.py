from __future__ import annotations

from stackops.scripts import windows as module


def test_wrap_mcfg_path_reference_points_to_powershell_wrapper() -> None:
    assert module.WRAP_MCFG_PATH_REFERENCE == "wrap_mcfg.ps1"
    assert module.WRAP_MCFG_PATH_REFERENCE.endswith(".ps1")
