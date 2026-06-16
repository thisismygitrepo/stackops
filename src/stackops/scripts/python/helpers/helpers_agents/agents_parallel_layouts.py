"""Generated layout helpers for parallel agent backends."""

import json
from pathlib import Path
from typing import cast

from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def read_generated_layouts(*, layout_output_path: Path) -> list[LayoutConfig]:
    try:
        raw_payload = json.loads(layout_output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Generated layout is not valid JSON: {layout_output_path}") from exc
    if not isinstance(raw_payload, dict):
        raise RuntimeError(f"Generated layout root must be a JSON object: {layout_output_path}")
    raw_layouts = raw_payload.get("layouts")
    if not isinstance(raw_layouts, list):
        raise RuntimeError(f"Generated layout must contain a layouts list: {layout_output_path}")
    return cast(list[LayoutConfig], raw_layouts)
