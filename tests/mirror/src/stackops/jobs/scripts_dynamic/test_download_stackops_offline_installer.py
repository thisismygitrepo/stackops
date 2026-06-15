from pathlib import Path

import pytest

from stackops.jobs.scripts_dynamic import download_stackops_offline_installer as downloader


def _url_map_with_target(target_pair: str, url: str) -> dict[str, str | None]:
    return {known_target: url if known_target == target_pair else None for known_target in downloader.KNOWN_TARGETS}


def test_default_output_dir_includes_selected_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    url = "https://example.test/linux-x64.zip"
    calls: list[tuple[str, Path]] = []

    def fake_download_and_extract(*, url: str, output_dir: Path) -> None:
        calls.append((url, output_dir))

    monkeypatch.setattr(downloader, "DEFAULT_OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(downloader, "_load_url_map", lambda: _url_map_with_target("linux-x64", url))
    monkeypatch.setattr(downloader, "_download_and_extract", fake_download_and_extract)

    resolved_output_dir = downloader.download_installer(target_key="linux-x64", output_dir=None)

    expected_output_dir = tmp_path.joinpath("stackops-offline-installer-linux-x64").resolve()
    assert resolved_output_dir == expected_output_dir
    assert calls == [(url, expected_output_dir)]


def test_explicit_output_dir_is_honored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    url = "https://example.test/macos-arm.zip"
    explicit_output_dir = tmp_path.joinpath("custom-installer")
    calls: list[tuple[str, Path]] = []

    def fake_download_and_extract(*, url: str, output_dir: Path) -> None:
        calls.append((url, output_dir))

    monkeypatch.setattr(downloader, "DEFAULT_OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(downloader, "_load_url_map", lambda: _url_map_with_target("macos-arm", url))
    monkeypatch.setattr(downloader, "_download_and_extract", fake_download_and_extract)

    resolved_output_dir = downloader.download_installer(target_key="macos-arm", output_dir=explicit_output_dir)

    expected_output_dir = explicit_output_dir.resolve()
    assert resolved_output_dir == expected_output_dir
    assert calls == [(url, expected_output_dir)]
