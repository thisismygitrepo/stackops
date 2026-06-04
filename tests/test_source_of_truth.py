import hashlib
import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile import _format_self_managed_mapper_path, get_backup_path
import stackops.utils.source_of_truth as source_of_truth
from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_MAPPER_FILES_ROOT, DOTFILES_ROOT, resolve_source_of_truth_path


def test_resolve_source_of_truth_path_expands_known_roots() -> None:
    assert resolve_source_of_truth_path("CONFIG_ROOT/settings/app.json") == (CONFIG_ROOT / "settings" / "app.json").absolute()
    assert resolve_source_of_truth_path("DOTFILES_ROOT/creds/app/config.toml") == (DOTFILES_ROOT / "creds" / "app" / "config.toml").absolute()


def test_format_self_managed_mapper_path_uses_dotfiles_root_token() -> None:
    assert _format_self_managed_mapper_path(DOTFILES_ROOT / "creds" / "app" / "config.toml") == "DOTFILES_ROOT/creds/app/config.toml"


def test_get_backup_path_uses_flat_hash_location_for_default_destination() -> None:
    original_path = Path.home() / "code/bytesense/.agents/skills/bot/bot-db.md"
    location_hash = hashlib.sha256("~/code/bytesense/.agents/skills/bot".encode("utf-8")).hexdigest()[:16]

    assert get_backup_path(original_path, sensitivity="private", destination=None, shared=False) == (
        DOTFILES_MAPPER_FILES_ROOT / f"{location_hash}.bot-db.md"
    )


def test_get_backup_path_ignores_sensitivity_and_shared_for_default_destination() -> None:
    original_path = Path.home() / "code/bytesense/.agents/skills/bot/bot-db.md"
    private_path = get_backup_path(original_path, sensitivity="private", destination=None, shared=False)

    assert get_backup_path(original_path, sensitivity="public", destination=None, shared=True) == private_path
    assert private_path.parent == DOTFILES_MAPPER_FILES_ROOT


def test_read_stackops_config_returns_schema_typed_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "repos": ["~/code/repo"],
                "rclone_config_name": "cloud",
                "email_config_name": "mail",
                "to_email": "user@example.com",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(source_of_truth, "DOTFILES_STACKOPS_CONFIG_PATH", config_path)

    config = source_of_truth.read_stackops_config()

    assert config["repos"] == ["~/code/repo"]
    assert source_of_truth.read_stackops_config_string("rclone_config_name") == "cloud"


def test_read_stackops_config_rejects_unknown_config_keys(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "repos": [],
                "rclone_config_name": "cloud",
                "email_config_name": "mail",
                "to_email": "user@example.com",
                "extra": "nope",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(source_of_truth, "DOTFILES_STACKOPS_CONFIG_PATH", config_path)

    with pytest.raises(ValueError, match="Unexpected StackOps config keys at root"):
        source_of_truth.read_stackops_config()
