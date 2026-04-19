

from stackops.jobs import installer


def test_installer_reference_constants_match_expected_files() -> None:
    assert installer.INSTALLER_DATA_PATH_REFERENCE == "installer_data.json"
    assert installer.PATH_EXTENDED_REPORT_PATH_REFERENCE == "path_extended_report.md"
    assert installer.TODO_PATH_REFERENCE == "todo.md"
