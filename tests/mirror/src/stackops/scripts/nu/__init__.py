from stackops.scripts.nu import WRAP_MCFG_PATH_REFERENCE


def test_wrap_mcfg_path_reference_matches_expected_file() -> None:
    assert WRAP_MCFG_PATH_REFERENCE == "wrap_mcfg.nu"
