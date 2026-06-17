from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPER_PATH = REPO_ROOT / "src" / "stackops" / "utils" / "schemas" / "mapper" / "dotfiles.yaml"
SETTINGS_ROOT = REPO_ROOT / "src" / "stackops" / "settings"
CONFIG_SETTINGS_PREFIX = "CONFIG_ROOT/settings/"


def test_library_mapper_config_settings_targets_are_packaged() -> None:
    mapper = yaml.safe_load(MAPPER_PATH.read_text(encoding="utf-8")) or {}
    missing_assets: list[str] = []

    for program_name, entries in mapper.items():
        for entry_name, entry in entries.items():
            self_managed = entry["self_managed"]
            if not self_managed.startswith(CONFIG_SETTINGS_PREFIX):
                continue

            relative_asset_path = self_managed.removeprefix(CONFIG_SETTINGS_PREFIX)
            packaged_asset_path = SETTINGS_ROOT / relative_asset_path
            if not packaged_asset_path.exists():
                missing_assets.append(
                    f"{program_name}.{entry_name}: {self_managed} -> {packaged_asset_path.relative_to(REPO_ROOT)}"
                )

    assert missing_assets == [], "Missing packaged settings assets:\n" + "\n".join(missing_assets)
