from pathlib import Path

import pytest

from stackops.jobs.scripts_dynamic import download_stackops_offline_installer


def test_parse_url_map_normalizes_known_targets() -> None:
    parsed = download_stackops_offline_installer._parse_url_map(
        raw_json='{"linux-x64": "https://example.com/linux.zip", "windows-arm": null}'
    )

    assert parsed == {
        "linux-x64": "https://example.com/linux.zip",
        "linux-arm": None,
        "macos-x64": None,
        "macos-arm": None,
        "windows-x64": None,
        "windows-arm": None,
    }


def test_build_targets_preserves_known_order() -> None:
    targets = download_stackops_offline_installer._build_targets(
        url_map={
            "linux-x64": "a",
            "linux-arm": "b",
            "macos-x64": "c",
            "macos-arm": "d",
            "windows-x64": "e",
            "windows-arm": "f",
        }
    )

    assert [target.pair for target in targets] == [
        "linux-x64",
        "linux-arm",
        "macos-x64",
        "macos-arm",
        "windows-x64",
        "windows-arm",
    ]


def test_resolve_downloaded_archive_requires_single_file(tmp_path: Path) -> None:
    tmp_path.joinpath("first.zip").write_text("a", encoding="utf-8")
    tmp_path.joinpath("second.zip").write_text("b", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Expected exactly one downloaded archive"):
        download_stackops_offline_installer._resolve_downloaded_archive(download_dir=tmp_path)
