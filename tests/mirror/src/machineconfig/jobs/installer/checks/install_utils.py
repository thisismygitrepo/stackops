from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from machineconfig.jobs.installer.checks import install_utils


class FakeConsole:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def print(self, message: object) -> None:
        self.messages.append(message)


class FakeThreadPoolExecutor:
    def __init__(self, max_workers: int) -> None:
        self.max_workers = max_workers

    def __enter__(self) -> FakeThreadPoolExecutor:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object | None) -> None:
        return None

    def map(self, function: object, values: list[str]) -> list[bool]:
        return [function(value) for value in values]


def test_load_csv_report_reads_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "report.csv"
    csv_path.write_text("app_name,app_url\nalpha,https://example.test/alpha\n", encoding="utf-8")

    assert install_utils._load_csv_report(csv_path) == [{"app_name": "alpha", "app_url": "https://example.test/alpha"}]


def test_upload_app_returns_share_link_and_handles_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(install_utils, "console", fake_console)
    app_path = tmp_path / "tool"
    app_path.write_text("binary", encoding="utf-8")

    monkeypatch.setattr(install_utils, "get_remote_path", lambda **kwargs: Path("myhome/tool"))
    monkeypatch.setattr(install_utils, "to_cloud", lambda **kwargs: "https://example.test/share")
    assert install_utils.upload_app(app_path) == "https://example.test/share"

    def fail_remote_path(**kwargs: object) -> Path:
        raise RuntimeError(f"boom: {kwargs!r}")

    monkeypatch.setattr(install_utils, "get_remote_path", fail_remote_path)
    assert install_utils.upload_app(app_path) is None
    assert any("Failed to upload" in str(message) for message in fake_console.messages)


def test_download_google_drive_file_extracts_file_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "download"
    output_dir.mkdir()
    captured: dict[str, str] = {}

    def fake_tmpdir(prefix: str) -> Path:
        assert prefix == "gdown_"
        return output_dir

    def fake_download(*, id: str, output: str, quiet: bool, fuzzy: bool) -> str:
        assert quiet is False
        assert fuzzy is True
        captured["id"] = id
        captured["output"] = output
        download_path = Path(output) / "tool.bin"
        download_path.write_text("binary", encoding="utf-8")
        return download_path.as_posix()

    monkeypatch.setattr(install_utils.PathExtended, "tmpdir", staticmethod(fake_tmpdir))
    fake_gdown = ModuleType("gdown")
    setattr(fake_gdown, "download", fake_download)
    monkeypatch.setitem(sys.modules, "gdown", fake_gdown)

    download_path = install_utils.download_google_drive_file("https://drive.google.com/file/d/file-123/view?usp=sharing")

    assert captured == {"id": "file-123", "output": f"{output_dir.as_posix()}/"}
    assert download_path.as_posix().endswith("tool.bin")


def test_install_cli_app_moves_binary_into_linux_install_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(install_utils, "console", fake_console)

    download_path = tmp_path / "tool"
    download_path.write_text("binary", encoding="utf-8")
    install_root = tmp_path / "bin"

    monkeypatch.setattr(install_utils, "download_google_drive_file", lambda url: download_path)
    monkeypatch.setattr(install_utils.platform, "system", lambda: "Linux")
    monkeypatch.setattr(install_utils, "LINUX_INSTALL_PATH", install_root.as_posix())

    assert install_utils.install_cli_app("https://example.test/tool") is True
    assert (install_root / "tool").exists() is True
    assert download_path.exists() is False


def test_load_report_helpers_and_download_safe_apps_filter_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    monkeypatch.setattr(install_utils, "console", fake_console)

    app_metadata_path = tmp_path / "apps.csv"
    engine_results_path = tmp_path / "engines.csv"
    app_metadata_path.write_text("app_name,app_url\nalpha,https://example.test/alpha\n", encoding="utf-8")
    engine_results_path.write_text("app_name,engine_name\nalpha,EngineA\n", encoding="utf-8")
    monkeypatch.setattr(install_utils, "APP_METADATA_PATH", app_metadata_path)
    monkeypatch.setattr(install_utils, "ENGINE_RESULTS_PATH", engine_results_path)

    assert install_utils.load_app_metadata_report() == [{"app_name": "alpha", "app_url": "https://example.test/alpha"}]
    assert install_utils.load_engine_results_report() == [{"app_name": "alpha", "engine_name": "EngineA"}]

    installed_urls: list[str] = []
    monkeypatch.setattr(
        install_utils,
        "load_app_metadata_report",
        lambda: [
            {"app_name": "alpha", "app_url": "https://example.test/alpha"},
            {"app_name": "beta", "app_url": "https://example.test/beta"},
            {"app_name": "gamma", "app_url": ""},
        ],
    )
    monkeypatch.setattr(install_utils, "install_cli_app", lambda url: installed_urls.append(url) or True)
    monkeypatch.setattr(install_utils, "ThreadPoolExecutor", FakeThreadPoolExecutor)

    install_utils.download_safe_apps("essentials")
    assert installed_urls == ["https://example.test/alpha", "https://example.test/beta"]

    installed_urls.clear()
    install_utils.download_safe_apps("beta")
    assert installed_urls == ["https://example.test/beta"]
