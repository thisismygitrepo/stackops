import hashlib
from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile import _format_self_managed_mapper_path, get_backup_path
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
