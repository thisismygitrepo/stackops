from __future__ import annotations

import machineconfig.utils.schemas.layouts as layouts_schema


def test_layout_schema_constants_point_to_expected_files() -> None:
    assert layouts_schema.LAYOUT_PATH_REFERENCE == "layout.json"
    assert layouts_schema.LAYOUT_SCHEMA_PATH_REFERENCE == "layout.schema.json"
