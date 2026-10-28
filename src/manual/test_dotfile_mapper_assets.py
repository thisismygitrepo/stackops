from pathlib import Path

from stackops.profile.dotfiles_mapper import LIBRARY_MAPPER_PATH, load_dotfiles_mapper


REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_ROOT = REPO_ROOT / "src" / "stackops" / "settings"
CONFIG_SETTINGS_PREFIX = "CONFIG_ROOT/settings/"


def test_library_mapper_config_settings_targets_are_packaged() -> None:
    mapper = load_dotfiles_mapper(LIBRARY_MAPPER_PATH)
    assert mapper, "Library mapper must contain packaged settings entries"
    missing_assets: list[str] = []

    for program_name, entries in mapper.items():
        for entry_name, entry in entries.items():
            self_managed = entry["self_managed"]
            assert self_managed.startswith(CONFIG_SETTINGS_PREFIX), f"""{program_name}.{entry_name}: {self_managed} is not a packaged setting"""

            relative_asset_path = self_managed.removeprefix(CONFIG_SETTINGS_PREFIX)
            packaged_asset_path = SETTINGS_ROOT / relative_asset_path
            if not packaged_asset_path.exists():
                missing_assets.append(
                    f"{program_name}.{entry_name}: {self_managed} -> {packaged_asset_path.relative_to(REPO_ROOT)}"
                )

    assert missing_assets == [], "Missing packaged settings assets:\n" + "\n".join(missing_assets)
