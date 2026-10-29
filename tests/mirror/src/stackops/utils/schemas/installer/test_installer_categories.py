import json
from typing import cast

import stackops.utils.schemas.installer as installer_schema_assets
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_categories import installer_category_definition
from stackops.utils.schemas.installer.installer_types import INSTALLER_CATEGORY_LABELS


def test_schema_category_enum_mirrors_python_category_definitions() -> None:
    schema_path = get_path_reference_path(module=installer_schema_assets, path_reference=installer_schema_assets.INSTALLER_DATA_SCHEMA_PATH_REFERENCE)
    schema = cast(dict[str, dict[str, dict[str, object]]], json.loads(schema_path.read_text(encoding="utf-8")))
    expected_one_of = [
        {
            "const": category_label,
            "title": installer_category_definition(label=category_label)["title"],
            "description": installer_category_definition(label=category_label)["description"],
        }
        for category_label in INSTALLER_CATEGORY_LABELS
    ]

    assert schema["definitions"]["InstallerCategory"]["oneOf"] == expected_one_of, f"""Replace definitions.InstallerCategory.oneOf in {schema_path} with:
{json.dumps(expected_one_of, indent=2, ensure_ascii=False)}"""
