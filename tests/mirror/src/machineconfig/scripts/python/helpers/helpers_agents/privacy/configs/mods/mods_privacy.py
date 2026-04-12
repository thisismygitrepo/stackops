from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy as mods_privacy_module
from machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy import (
    secure_mods_config,
)


def raise_os_error(_path: object, _mode: int) -> None:
    raise OSError("chmod failed")


def test_secure_mods_config_updates_existing_keys_and_appends_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    config_file = tmp_path / "xdg" / "mods" / "mods.yml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        "# keep\ntelemetry: true\nextra: keep\n  # no-cache: false\n",
        encoding="utf-8",
    )

    secure_mods_config()

    assert config_file.read_text(encoding="utf-8") == (
        "# keep\n"
        "telemetry: false\n"
        "extra: keep\n"
        "no-cache: true\n"
        'cache-path: "/dev/null"\n'
    )


def test_secure_mods_config_creates_default_file_when_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(mods_privacy_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(mods_privacy_module.os, "chmod", raise_os_error)

    secure_mods_config()

    config_file = tmp_path / ".config" / "mods" / "mods.yml"
    assert config_file.read_text(encoding="utf-8") == (
        "no-cache: true\n"
        'cache-path: "/dev/null"\n'
        "telemetry: false\n"
    )
