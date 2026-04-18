from stackops.scripts.nu import WRAP_STACKOPS_PATH_REFERENCE


def test_wrap_stackops_path_reference_matches_expected_file() -> None:
    assert WRAP_STACKOPS_PATH_REFERENCE == "wrap_stackops.nu"
