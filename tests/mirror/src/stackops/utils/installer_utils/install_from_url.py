from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from rich.console import Console

import stackops.utils.installer_utils.install_from_url as install_from_url
from stackops.utils.path_extended import PathExtended


@dataclass(slots=True)
class ConsoleSpy:
    messages: list[object]

    def print(self, message: object) -> None:
        self.messages.append(message)


def test_finalize_install_moves_binary_and_records_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    versions_root = tmp_path.joinpath("versions")
    extracted_path = PathExtended(tmp_path.joinpath("downloaded-tool"))
    extracted_path.write_text("payload", encoding="utf-8")
    installed_path = PathExtended(tmp_path.joinpath("bin", "mytool"))
    install_calls: list[tuple[str | None, str | None, bool]] = []
    console = Console(record=True)

    def fake_find_move_delete_linux(
        *,
        downloaded: PathExtended,
        tool_name: str | None,
        delete: bool,
        rename_to: str | None,
    ) -> PathExtended:
        assert downloaded == extracted_path
        install_calls.append((tool_name, rename_to, delete))
        installed_path.parent.mkdir(parents=True, exist_ok=True)
        installed_path.write_text("installed", encoding="utf-8")
        return installed_path

    finalize_install = cast(Callable[..., None], getattr(install_from_url, "_finalize_install"))

    monkeypatch.setattr(install_from_url, "find_move_delete_linux", fake_find_move_delete_linux)
    monkeypatch.setattr(install_from_url.platform, "system", lambda: "Linux")
    monkeypatch.setattr(install_from_url, "INSTALL_VERSION_ROOT", versions_root)

    finalize_install(
        repo_name="owner/my-tool",
        asset_name="tool.tar.gz",
        version="v1.2.3",
        extracted_path=extracted_path,
        console=console,
    )

    assert install_calls == [("mytool", "mytool", True)]
    assert versions_root.joinpath("mytool").read_text(encoding="utf-8") == "v1.2.3"


def test_install_from_github_url_selects_asset_and_finalizes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    console = ConsoleSpy(messages=[])
    expected_console = console
    selected_labels: list[str] = []
    downloaded_urls: list[str] = []
    finalized_calls: list[tuple[str, str | None, str, PathExtended]] = []
    extracted_path = PathExtended(tmp_path.joinpath("tool.tar.gz"))
    extracted_path.write_text("payload", encoding="utf-8")

    def fake_choose_from_options(
        *,
        options: list[str],
        msg: str,
        multi: bool,
        header: str,
        tv: bool,
    ) -> str | None:
        assert msg == "Select a release asset"
        assert multi is False
        assert header == "📦 GitHub Release Assets"
        assert tv is True
        selected_labels.extend(options)
        return options[0]

    def fake_download_and_prepare(download_url: str) -> PathExtended:
        downloaded_urls.append(download_url)
        return extracted_path

    def fake_finalize(
        repo_name: str,
        asset_name: str | None,
        version: str,
        extracted_path: PathExtended,
        console: ConsoleSpy,
    ) -> None:
        assert console is expected_console
        finalized_calls.append((repo_name, asset_name, version, extracted_path))

    monkeypatch.setattr(install_from_url, "get_repo_name_from_url", lambda github_url: ("owner", "repo"))
    monkeypatch.setattr(install_from_url, "fetch_github_release_data", lambda owner, repo: {"ignored": True})
    monkeypatch.setattr(
        install_from_url,
        "extract_release_info",
        lambda release_raw: {
            "tag_name": "v1.0.0",
            "name": "Release 1",
            "published_at": "2024-01-05T12:00:00Z",
            "assets": [
                {
                    "name": "tool.tar.gz",
                    "size": 7168,
                    "download_count": 12,
                    "content_type": "application/gzip",
                    "created_at": "2024-01-05T12:00:00Z",
                    "updated_at": "2024-01-05T12:00:00Z",
                    "browser_download_url": "https://downloads.example/tool.tar.gz",
                }
            ],
            "assets_count": 1,
        },
    )
    monkeypatch.setattr(install_from_url, "download_and_prepare", fake_download_and_prepare)
    monkeypatch.setattr(install_from_url, "_finalize_install", fake_finalize)
    monkeypatch.setattr("stackops.utils.options.choose_from_options", fake_choose_from_options)
    monkeypatch.setattr("rich.console.Console", lambda: console)

    install_from_url.install_from_github_url("https://github.com/owner/repo")

    assert downloaded_urls == ["https://downloads.example/tool.tar.gz"]
    assert finalized_calls == [("owner/repo", "tool.tar.gz", "v1.0.0", extracted_path)]
    assert len(selected_labels) == 1
    assert "tool.tar.gz" in selected_labels[0]
    assert "7.0 KiB" in selected_labels[0]
    assert "2024-01-05" in selected_labels[0]


def test_install_from_binary_url_delegates_to_finalize(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    finalized_calls: list[tuple[str, str | None, str, PathExtended]] = []
    extracted_path = PathExtended(tmp_path.joinpath("tool"))
    extracted_path.write_text("payload", encoding="utf-8")
    console = ConsoleSpy(messages=[])

    monkeypatch.setattr(install_from_url, "download_and_prepare", lambda binary_url: extracted_path)
    monkeypatch.setattr(
        install_from_url,
        "_finalize_install",
        lambda repo_name, asset_name, version, extracted_path, console: finalized_calls.append(
            (repo_name, asset_name, version, extracted_path)
        ),
    )
    monkeypatch.setattr("rich.console.Console", lambda: console)

    install_from_url.install_from_binary_url("https://downloads.example/tool")

    assert finalized_calls == [("", None, "latest", extracted_path)]
