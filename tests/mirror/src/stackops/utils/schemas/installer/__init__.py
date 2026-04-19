

import stackops.utils.schemas.installer as installer_schema


def test_installer_schema_reference_matches_expected_filename() -> None:
    assert installer_schema.INSTALLER_TYPE_SCHEMA_PATH_REFERENCE == "installer_type.schema.json"
