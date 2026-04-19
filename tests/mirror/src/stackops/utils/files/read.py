

from pathlib import Path
from typing import cast

import pytest

from stackops.utils.files.read import read_file, read_ini, read_json, read_jsonl


def test_read_json_allows_c_style_comments_without_stripping_urls(tmp_path: Path) -> None:
    json_path = tmp_path.joinpath("config.json")
    json_path.write_text(
        """
        {
          "url": "https://example.com/api//v1",
          /* keep url intact */
          "enabled": true, // trailing comment
          "name": "tool"
        }
        """.strip(),
        encoding="utf-8",
    )

    parsed = cast(dict[str, object], read_json(json_path))
    parsed_via_dispatch = cast(dict[str, object], read_file(json_path))

    assert parsed == {"url": "https://example.com/api//v1", "enabled": True, "name": "tool"}
    assert parsed_via_dispatch == parsed


def test_read_file_rejects_directory_paths(tmp_path: Path) -> None:
    with pytest.raises(IsADirectoryError, match="directory"):
        read_file(tmp_path)


def test_read_file_requires_known_non_empty_suffix(tmp_path: Path) -> None:
    suffixless_path = tmp_path.joinpath("config")
    suffixless_path.write_text("value", encoding="utf-8")
    unknown_path = tmp_path.joinpath("config.unknown")
    unknown_path.write_text("value", encoding="utf-8")

    with pytest.raises(ValueError, match="Suffix is empty"):
        read_file(suffixless_path)
    with pytest.raises(AttributeError, match="Unknown file type"):
        read_file(unknown_path)


def test_read_jsonl_raises_on_invalid_line(tmp_path: Path) -> None:
    jsonl_path = tmp_path.joinpath("records.jsonl")
    jsonl_path.write_text('{"ok": 1}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError):
        read_jsonl(jsonl_path)


def test_read_ini_requires_existing_file(tmp_path: Path) -> None:
    missing_path = tmp_path.joinpath("settings.ini")

    with pytest.raises(FileNotFoundError, match="File not found"):
        read_ini(missing_path)
