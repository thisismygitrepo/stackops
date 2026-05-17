import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_sessions import utils


def test_balance_load_accepts_layout_files_with_comments(
    tmp_path: Path,
) -> None:
    layout_path = tmp_path / "layout.json"
    output_path = tmp_path / "balanced.json"
    layout_path.write_text(
        """
        {
            // this file intentionally contains comments
            "version": "0.1",
            "layouts": [
                {
                    "layoutName": "demo",
                    "layoutTabs": [
                        {"tabName": "one", "startDir": "~/", "command": "echo one"},
                        {"tabName": "two", "startDir": "~/", "command": "echo two"}
                    ]
                }
            ]
        }
        """,
        encoding="utf-8",
    )

    utils.balance_load(
        layout_path=str(layout_path),
        max_thresh=1,
        thresh_type="number",
        breaking_method="moreLayouts",
        output_path=str(output_path),
    )

    balanced_layout = json.loads(output_path.read_text(encoding="utf-8"))

    assert [layout["layoutName"] for layout in balanced_layout["layouts"]] == [
        "demo_part1",
        "demo_part2",
    ]


def test_balance_load_rejects_missing_layout_file(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match="Layout file not found"):
        utils.balance_load(
            layout_path=str(missing_path),
            max_thresh=1,
            thresh_type="number",
            breaking_method="moreLayouts",
            output_path=None,
        )


def test_balance_load_requires_layouts_field(
    tmp_path: Path,
) -> None:
    invalid_layout_path = tmp_path / "layout.json"
    invalid_layout_path.write_text(
        json.dumps({"version": "0.1"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required 'layouts' field"):
        utils.balance_load(
            layout_path=str(invalid_layout_path),
            max_thresh=1,
            thresh_type="number",
            breaking_method="moreLayouts",
            output_path=None,
        )
