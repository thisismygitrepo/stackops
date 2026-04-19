

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

import stackops.jobs.installer.python_scripts.cursor as cursor_script
from stackops.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {})


@dataclass(frozen=True)
class CompletedProcessStub:
    returncode: int = 0


@dataclass(frozen=True)
class RunCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]


def test_install_linux_moves_appimage_and_writes_desktop_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_dir = tmp_path / "home"
    downloads_dir = home_dir / "Downloads"
    downloads_dir.mkdir(parents=True)
    appimage_path = downloads_dir / "Cursor-1.0.AppImage"
    appimage_path.write_text("appimage", encoding="utf-8")
    install_root = tmp_path / "bin"

    chmod_calls: list[tuple[object, int]] = []
    run_calls: list[RunCall] = []

    def fake_run(*args: object, **kwargs: object) -> CompletedProcessStub:
        run_calls.append(RunCall(args=args, kwargs=dict(kwargs)))
        return CompletedProcessStub()

    def fake_chmod(path: object, mode: int) -> None:
        chmod_calls.append((path, mode))

    monkeypatch.setattr(cursor_script.Path, "home", lambda: home_dir)
    monkeypatch.setattr(cursor_script, "LINUX_INSTALL_PATH", str(install_root))
    monkeypatch.setattr(cursor_script.os, "chmod", fake_chmod)
    monkeypatch.setattr(cursor_script.subprocess, "run", fake_run)

    cursor_script.install_linux(version=None)

    installed_binary = install_root / "cursor"
    desktop_file = home_dir / ".local/share/applications/cursor.desktop"

    assert installed_binary.exists()
    assert not appimage_path.exists()
    assert "Exec=" + str(installed_binary) in desktop_file.read_text(encoding="utf-8")
    assert "Icon=cursor" in desktop_file.read_text(encoding="utf-8")
    assert chmod_calls
    assert run_calls == [RunCall(args=(["update-desktop-database", str(home_dir / ".local/share/applications")],), kwargs={"check": False})]


def test_main_unsupported_platform_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cursor_script.platform, "system", lambda: "Darwin")

    with pytest.raises(OSError, match="Unsupported operating system: Darwin"):
        cursor_script.main(installer_data=DUMMY_INSTALLER_DATA, version=None, update=False)
