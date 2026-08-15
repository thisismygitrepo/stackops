import json
from typing import cast

import yaml
from jsonschema.validators import Draft7Validator

import stackops.utils.schemas.mapper as mapper_assets
from stackops.profile.dotfiles_mapper import load_dotfiles_mapper
from stackops.utils.path_reference import get_path_reference_path


def test_dotfiles_mapper_matches_schema() -> None:
    mapper_path = get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DOTFILES_PATH_REFERENCE)
    schema_path = get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE)
    schema = cast(dict[str, object], json.loads(schema_path.read_text(encoding="utf-8")))
    mapper_data = cast(object, yaml.safe_load(mapper_path.read_text(encoding="utf-8")))

    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(mapper_data)


def test_rustdesk_mapper_covers_client_and_selected_server_state() -> None:
    mapper_path = get_path_reference_path(module=mapper_assets, path_reference=mapper_assets.MAPPER_DOTFILES_PATH_REFERENCE)
    mapper = load_dotfiles_mapper(mapper_path)

    assert mapper["rustdesk_client"] == {
        "linux": {"original": "~/.config/rustdesk", "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/client/config", "os": ["linux"]},
        "windows": {
            "original": "~/AppData/Roaming/RustDesk/config",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/client/config",
            "os": ["windows"],
        },
        "darwin": {
            "original": "~/Library/Preferences/com.carriez.RustDesk",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/client/config",
            "os": ["darwin"],
        },
    }
    assert mapper["rustdesk_client_service"] == {
        "linux": {"original": "/root/.config/rustdesk", "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/client_service/config", "os": ["linux"]},
        "windows": {
            "original": "C:/Windows/ServiceProfiles/LocalService/AppData/Roaming/RustDesk/config",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/client_service/config",
            "os": ["windows"],
        },
        "darwin": {
            "original": "/Library/Preferences/com.carriez.RustDesk",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/client_service/config",
            "os": ["darwin"],
        },
    }
    assert mapper["rustdesk_server"] == {
        "private_key": {
            "original": "~/rustdesk-server/data/id_ed25519",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/server/data/id_ed25519",
            "os": ["linux", "windows"],
        },
        "public_key": {
            "original": "~/rustdesk-server/data/id_ed25519.pub",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/server/data/id_ed25519.pub",
            "os": ["linux", "windows"],
        },
        "config": {
            "original": "~/rustdesk-server/data/.config",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/server/data/.config",
            "os": ["linux", "windows"],
        },
        "compose": {
            "original": "~/rustdesk-server/compose.yml",
            "self_managed": "DOTFILES_ROOT/creds/RDP/rustdesk/server/compose.yml",
            "os": ["linux", "windows"],
        },
    }
