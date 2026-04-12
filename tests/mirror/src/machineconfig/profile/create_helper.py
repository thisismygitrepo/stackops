from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from machineconfig.profile import create_helper as create_helper_module


def _call_copy_path(source: Path, target: Path, overwrite: bool) -> None:
    copy_path = cast(Callable[[Path, Path, bool], None], getattr(create_helper_module, "_copy_path"))
    copy_path(source, target, overwrite)


def test_copy_path_rejects_existing_target_without_overwrite_then_replaces_it(tmp_path: Path) -> None:
    source_path = tmp_path / "source.txt"
    target_path = tmp_path / "target.txt"
    source_path.write_text("new contents", encoding="utf-8")
    target_path.write_text("old contents", encoding="utf-8")

    with pytest.raises(FileExistsError, match="overwrite=False"):
        _call_copy_path(source=source_path, target=target_path, overwrite=False)

    _call_copy_path(source=source_path, target=target_path, overwrite=True)

    assert target_path.read_text(encoding="utf-8") == "new contents"


def test_copy_path_copies_directory_tree(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.joinpath("nested").mkdir(parents=True)
    source_dir.joinpath("nested", "config.txt").write_text("payload", encoding="utf-8")

    _call_copy_path(source=source_dir, target=target_dir, overwrite=True)

    assert target_dir.joinpath("nested", "config.txt").read_text(encoding="utf-8") == "payload"


def test_copy_assets_to_machine_for_scripts_copies_all_packaged_files_and_wrap_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    library_root = tmp_path / "library"
    config_root = tmp_path / "config"
    scripts_root = library_root / "scripts" / "linux"
    wrap_script_path = tmp_path / "wrap_mcfg.nu"
    scripts_root.joinpath("bin").mkdir(parents=True)
    scripts_root.joinpath("bin", "alpha.sh").write_text("echo alpha", encoding="utf-8")
    scripts_root.joinpath("beta.txt").write_text("beta", encoding="utf-8")
    wrap_script_path.write_text("source-env ./machineconfig.nu", encoding="utf-8")

    copy_calls: list[tuple[Path, Path, bool]] = []
    chmod_calls: list[str] = []

    def fake_copy_path(source: Path, target: Path, overwrite: bool) -> None:
        copy_calls.append((source, target, overwrite))

    def fake_subprocess_run(command: str, *, shell: bool, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert shell is True
        assert capture_output is True
        assert text is True
        assert check is False
        chmod_calls.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(create_helper_module, "LIBRARY_ROOT", library_root)
    monkeypatch.setattr(create_helper_module, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(create_helper_module, "_copy_path", fake_copy_path)
    monkeypatch.setattr(create_helper_module, "get_path_reference_path", lambda module, path_reference: wrap_script_path)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    create_helper_module.copy_assets_to_machine("scripts")

    copied_targets = {target.relative_to(config_root) for _, target, _ in copy_calls}

    assert copied_targets == {Path("scripts/bin/alpha.sh"), Path("scripts/beta.txt"), Path("scripts/wrap_mcfg.nu")}
    assert all(overwrite for _, _, overwrite in copy_calls)
    assert chmod_calls == [f"chmod +x {config_root.joinpath('scripts')} -R"]
