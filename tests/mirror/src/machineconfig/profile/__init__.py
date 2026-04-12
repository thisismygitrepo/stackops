from __future__ import annotations

import json
from pathlib import Path

import yaml

import machineconfig.profile as profile_assets
from machineconfig.utils.path_reference import get_path_reference_path


def _resolve_profile_asset(path_reference: str) -> Path:
    return get_path_reference_path(module=profile_assets, path_reference=path_reference)


def test_packaged_yaml_mapper_files_exist_and_load_as_mappings() -> None:
    for path_reference in (
        profile_assets.MAPPER_DATA_PATH_REFERENCE,
        profile_assets.MAPPER_DOTFILES_PATH_REFERENCE,
    ):
        asset_path = _resolve_profile_asset(path_reference)
        loaded_obj = yaml.safe_load(asset_path.read_text(encoding="utf-8"))

        assert asset_path.is_file()
        assert isinstance(loaded_obj, dict)
        assert len(loaded_obj) > 0


def test_packaged_json_schema_files_exist_and_load_as_objects() -> None:
    for path_reference in (
        profile_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE,
        profile_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE,
    ):
        asset_path = _resolve_profile_asset(path_reference)
        loaded_obj = json.loads(asset_path.read_text(encoding="utf-8"))

        assert asset_path.is_file()
        assert isinstance(loaded_obj, dict)
        assert len(loaded_obj) > 0
