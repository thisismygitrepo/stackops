

from pathlib import Path
import subprocess

import pytest

import stackops.utils.installer_utils.installer_helper as installer_helper
from stackops.utils.path_extended import PathExtended
from stackops.utils.schemas.installer.installer_types import InstallerData


def _make_installer_data(app_name: str, doc: str) -> InstallerData:
    return {
        "appName": app_name,
        "license": "MIT",
        "doc": doc,
        "repoURL": "https://github.com/example/repo",
        "fileNamePattern": {
            "amd64": {"windows": None, "linux": "tool-{version}.tar.gz", "darwin": None},
            "arm64": {"windows": None, "linux": "tool-{version}.tar.gz", "darwin": None},
        },
    }


def test_get_group_name_to_repr_formats_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer_helper, "PACKAGE_GROUP2NAMES", {"tools": ["alpha", "beta"]})

    result = installer_helper.get_group_name_to_repr()

    assert list(result.values()) == ["tools"]
    display_label = next(iter(result))
    assert display_label.startswith("Package ") is False
    assert display_label.startswith("📦 tools")
    assert "alpha|beta" in display_label


def test_handle_installer_not_found_returns_selected_app_names(monkeypatch: pytest.MonkeyPatch) -> None:
    installers = [_make_installer_data("git", "version control"), _make_installer_data("lazygit", "git tui")]

    def fake_choose_from_options(*, options: list[str], msg: str, multi: bool, tv: bool) -> list[str] | None:
        assert multi is True
        assert tv is True
        assert "git" in msg
        return [options[0]]

    monkeypatch.setattr("stackops.utils.options.choose_from_options", fake_choose_from_options)

    result = installer_helper.handle_installer_not_found("git", installers)

    assert result == ["git"]


def test_install_deb_package_removes_downloaded_file_even_on_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    deb_path = tmp_path.joinpath("tool.deb")
    deb_path.write_text("deb", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args=args, returncode=1, stdout="out", stderr="err"))

    installer_helper.install_deb_package(deb_path)

    assert not deb_path.exists()


def test_download_and_prepare_decompresses_nested_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    outer_archive = PathExtended(tmp_path.joinpath("bundle.zip"))
    outer_archive.write_text("archive", encoding="utf-8")
    first_extract = PathExtended(tmp_path.joinpath("bundle"))
    first_extract.mkdir()
    inner_archive = PathExtended(first_extract.joinpath("inner.gz"))
    inner_archive.write_text("nested", encoding="utf-8")
    final_extract = PathExtended(tmp_path.joinpath("binary"))
    final_extract.write_text("tool", encoding="utf-8")
    decompressed_paths: list[str] = []
    deleted_paths: list[str] = []

    def fake_download(download_url: str, output_dir: str) -> str:
        assert download_url == "https://downloads.example/bundle.zip"
        assert output_dir == str(installer_helper.INSTALL_TMP_DIR)
        return str(outer_archive)

    def fake_decompress(path: PathExtended) -> PathExtended:
        decompressed_paths.append(str(path))
        if path == outer_archive:
            return first_extract
        if path == inner_archive:
            return final_extract
        raise AssertionError(f"unexpected decompress target: {path}")

    def fake_delete(path: PathExtended, sure: bool, verbose: bool = True) -> PathExtended:
        _ = verbose
        assert sure is True
        deleted_paths.append(str(path))
        if path.exists() and path.is_file():
            path.unlink(missing_ok=True)
        return path

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_utils.download.download", fake_download)
    monkeypatch.setattr(PathExtended, "decompress", fake_decompress)
    monkeypatch.setattr(PathExtended, "delete", fake_delete)

    result = installer_helper.download_and_prepare("https://downloads.example/bundle.zip")

    assert result == final_extract
    assert decompressed_paths == [str(outer_archive), str(inner_archive)]
    assert deleted_paths == [str(outer_archive), str(inner_archive)]
