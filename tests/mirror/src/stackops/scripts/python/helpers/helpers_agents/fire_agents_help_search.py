from __future__ import annotations

from pathlib import Path

import stackops.scripts.python.helpers.helpers_agents.fire_agents_help_search as search_module


def test_search_files_by_pattern_skips_excluded_directories(tmp_path: Path) -> None:
    excluded_dir_name = next(iter(search_module.EXCLUDE_DIRS))
    included_dir = tmp_path / "src"
    excluded_dir = tmp_path / excluded_dir_name
    included_dir.mkdir()
    excluded_dir.mkdir()
    kept_file = included_dir / "config.yaml"
    skipped_file = excluded_dir / "config.yaml"
    kept_file.write_text("keep", encoding="utf-8")
    skipped_file.write_text("skip", encoding="utf-8")

    matches = search_module.search_files_by_pattern(tmp_path, "*.yaml")

    assert matches == [kept_file]


def test_search_python_files_is_case_insensitive_and_python_only(tmp_path: Path) -> None:
    excluded_dir_name = next(iter(search_module.EXCLUDE_DIRS))
    source_dir = tmp_path / "src"
    excluded_dir = tmp_path / excluded_dir_name
    source_dir.mkdir()
    excluded_dir.mkdir()
    wanted = source_dir / "worker.py"
    ignored_text = source_dir / "notes.txt"
    ignored_excluded = excluded_dir / "hidden.py"
    wanted.write_text("VALUE = 'Needle'\n", encoding="utf-8")
    ignored_text.write_text("needle", encoding="utf-8")
    ignored_excluded.write_text("needle", encoding="utf-8")

    matches = search_module.search_python_files(tmp_path, "needle")

    assert matches == [wanted]
