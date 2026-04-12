from __future__ import annotations

import json
from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy as cursor_privacy


def _patch_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr(cursor_privacy.Path, "home", lambda: home)


@pytest.mark.parametrize(
    ("system_name", "relative_path"),
    (
        ("Windows", Path("AppData") / "Roaming" / "Cursor" / "User" / "settings.json"),
        ("Darwin", Path("Library") / "Application Support" / "Cursor" / "User" / "settings.json"),
        ("Linux", Path(".config") / "Cursor" / "User" / "settings.json"),
    ),
)
def test_secure_cursor_cli_creates_platform_specific_settings_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, system_name: str, relative_path: Path
) -> None:
    home = tmp_path / system_name.lower()

    _patch_home(monkeypatch=monkeypatch, home=home)
    monkeypatch.setattr(cursor_privacy.platform, "system", lambda: system_name)

    cursor_privacy.secure_cursor_cli()

    settings_file = home / relative_path
    settings_data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert settings_file.is_file()
    assert settings_data["telemetry.telemetryLevel"] == "off"
    assert settings_data["cursor.privacyMode"] is True
    assert settings_data["extensions.autoUpdate"] is False


def test_secure_cursor_cli_strips_comments_and_preserves_existing_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    settings_file = home / ".config" / "Cursor" / "User" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        """// leading comment
{"keep": "value"}
/* trailing comment */
""",
        encoding="utf-8",
    )

    _patch_home(monkeypatch=monkeypatch, home=home)
    monkeypatch.setattr(cursor_privacy.platform, "system", lambda: "Linux")

    cursor_privacy.secure_cursor_cli()

    settings_data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert settings_data["keep"] == "value"
    assert settings_data["search.followSymlinks"] is False
    assert settings_data["git.openRepositoryInParentFolders"] == "never"
