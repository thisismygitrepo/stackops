import platform
import stat
from pathlib import Path

import pytest

from stackops.profile import create_helper


def _write_asset(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o644)


def test_copy_assets_to_machine_makes_darwin_wrapper_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    library_root = tmp_path / "library"
    config_root = tmp_path / "config"
    _write_asset(library_root / "scripts" / "linux" / "wrap_stackops", "#!/usr/bin/env bash\n")
    _write_asset(library_root / "scripts" / "nu" / "wrap_stackops.nu", "# nu wrapper\n")

    monkeypatch.setattr(create_helper, "LIBRARY_ROOT", library_root)
    monkeypatch.setattr(create_helper, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(platform, "system", lambda: "Darwin")

    create_helper.copy_assets_to_machine(which="scripts")

    wrapper_path = config_root / "scripts" / "wrap_stackops"
    assert wrapper_path.is_file()
    assert wrapper_path.stat().st_mode & stat.S_IXUSR
