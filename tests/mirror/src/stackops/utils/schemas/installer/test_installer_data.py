import json
import re
from typing import cast

from jsonschema.validators import Draft7Validator

import stackops.utils.schemas.installer as installer_schema_assets
from stackops.utils.installer_utils.linux_package_manager import LINUX_PACKAGE_MANAGERS
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import (
    LinuxPackageManagerInstallerPattern,
)


_NATIVE_LINUX_PATTERN = re.compile(
    r"(^|[\s;&|()])((/[A-Za-z0-9_.+-]+)+/)?(apt|apt-get|nala|dnf|yum)(\s|$)|\.([dD][eE][bB]|[rR][pP][mM])($|[^A-Za-z0-9])",
)


def test_installer_catalog_uses_explicit_native_package_mappings() -> None:
    catalog_path = get_path_reference_path(
        module=installer_schema_assets,
        path_reference=installer_schema_assets.INSTALLER_DATA_PATH_REFERENCE,
    )
    schema_path = get_path_reference_path(
        module=installer_schema_assets,
        path_reference=installer_schema_assets.INSTALLER_TYPE_SCHEMA_PATH_REFERENCE,
    )
    schema = cast(dict[str, object], json.loads(schema_path.read_text(encoding="utf-8")))
    catalog = cast(dict[str, object], json.loads(catalog_path.read_text(encoding="utf-8")))

    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(catalog)
    installers = cast(list[dict[str, object]], catalog["installers"])
    for installer in installers:
        file_name_patterns = cast(dict[str, dict[str, object]], installer["fileNamePattern"])
        assert set(file_name_patterns) == {"amd64", "arm64"}
        for architecture_patterns in file_name_patterns.values():
            assert set(architecture_patterns) == {"windows", "linux", "darwin"}
            linux_pattern = architecture_patterns["linux"]
            if isinstance(linux_pattern, dict):
                assert set(linux_pattern) == {"apt", "dnf"}
                assert all(
                    pattern is None or isinstance(pattern, str)
                    for pattern in linux_pattern.values()
                )
                continue
            assert linux_pattern is None or isinstance(linux_pattern, str)
            if isinstance(linux_pattern, str):
                assert _NATIVE_LINUX_PATTERN.search(linux_pattern) is None


def test_linux_manager_axes_stay_synchronized() -> None:
    schema_path = get_path_reference_path(
        module=installer_schema_assets,
        path_reference=installer_schema_assets.INSTALLER_TYPE_SCHEMA_PATH_REFERENCE,
    )
    schema = cast(dict[str, object], json.loads(schema_path.read_text(encoding="utf-8")))
    definitions = cast(dict[str, object], schema["definitions"])
    manager_mapping = cast(
        dict[str, object],
        definitions["LinuxPackageManagerInstallerPattern"],
    )
    schema_properties = cast(dict[str, object], manager_mapping["properties"])
    schema_required = cast(list[str], manager_mapping["required"])
    typed_keys = set(LinuxPackageManagerInstallerPattern.__annotations__)
    canonical_keys = set(LINUX_PACKAGE_MANAGERS)

    assert typed_keys == canonical_keys
    assert set(schema_properties) == canonical_keys
    assert set(schema_required) == canonical_keys
