from pathlib import Path
import re

import pytest

import machineconfig.scripts.python.helpers.helpers_devops.backup_config as backup_config_module


_INVALID_BACKUP_CONFIGS: list[tuple[dict[str, object], str]] = [
    (
        {
            "group": {
                "item": {
                    "path": "~/.bashrc",
                    "path_cloud": "^",
                    "zip": True,
                    "encrypt": True,
                    "rel2home": True,
                    "os": ["linux"],
                }
            }
        },
        "uses 'path'; use 'path_local' instead.",
    ),
    (
        {
            "group": {
                "item": {
                    "path_local": "~/.bashrc",
                    "path_cloud": "^",
                    "zip": True,
                    "encrypt": True,
                    "rel2home": True,
                    "os": ["linux"],
                    "unexpected": "boom",
                }
            }
        },
        "unsupported fields: unexpected.",
    ),
]


class _SilentConsole:
    def print(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.mark.parametrize(("raw_config", "message"), _INVALID_BACKUP_CONFIGS)
def test_parse_backup_config_rejects_invalid_fields(
    raw_config: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        backup_config_module._parse_backup_config(raw_config)


def test_load_backup_config_returns_none_for_empty_and_non_mapping_yaml(
    tmp_path: Path,
) -> None:
    empty_path = tmp_path / "empty.yaml"
    sequence_path = tmp_path / "sequence.yaml"
    missing_path = tmp_path / "missing.yaml"

    empty_path.write_text("", encoding="utf-8")
    sequence_path.write_text("- item\n", encoding="utf-8")

    assert backup_config_module._load_backup_config(missing_path) is None
    assert backup_config_module._load_backup_config(empty_path) is None
    assert backup_config_module._load_backup_config(sequence_path) is None


def test_write_and_read_backup_config_round_trip_and_merge_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library_path = tmp_path / "library.yaml"
    user_path = tmp_path / "user.yaml"
    monkeypatch.setattr(backup_config_module, "LIBRARY_BACKUP_PATH", library_path)
    monkeypatch.setattr(backup_config_module, "USER_BACKUP_PATH", user_path)
    monkeypatch.setattr(backup_config_module, "Console", _SilentConsole)

    library_config: backup_config_module.BackupConfig = {
        "dotfiles": {
            "bash": {
                "path_local": "~/.bashrc",
                "path_cloud": "^",
                "zip": True,
                "encrypt": False,
                "rel2home": True,
                "os": {"linux"},
            }
        }
    }
    user_config: backup_config_module.BackupConfig = {
        "secrets": {
            "tokens": {
                "path_local": "~/secrets",
                "path_cloud": None,
                "zip": False,
                "encrypt": True,
                "rel2home": True,
                "os": {"linux", "darwin"},
            }
        }
    }

    backup_config_module.write_backup_config(library_path, library_config)
    backup_config_module.write_backup_config(user_path, user_config)

    assert backup_config_module.read_backup_config(repo="library") == library_config
    assert backup_config_module.read_backup_config(repo="user") == user_config
    assert backup_config_module.read_backup_config(repo="all") == {
        **library_config,
        **user_config,
    }

    serialized_user_config = user_path.read_text(encoding="utf-8")
    assert serialized_user_config.startswith(backup_config_module.DEFAULT_BACKUP_HEADER)
    assert serialized_user_config.index("- linux") < serialized_user_config.index(
        "- darwin"
    )


def test_describe_missing_backup_config_reports_precise_path_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_user_path = tmp_path / "missing-user.yaml"
    directory_user_path = tmp_path / "directory-user.yaml"
    invalid_library_path = tmp_path / "invalid-library.yaml"

    monkeypatch.setattr(backup_config_module, "USER_BACKUP_PATH", missing_user_path)
    assert "does not exist" in backup_config_module.describe_missing_backup_config(
        repo="user"
    )

    directory_user_path.mkdir()
    monkeypatch.setattr(backup_config_module, "USER_BACKUP_PATH", directory_user_path)
    assert "not a file" in backup_config_module.describe_missing_backup_config(
        repo="user"
    )

    invalid_library_path.write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(
        backup_config_module,
        "LIBRARY_BACKUP_PATH",
        invalid_library_path,
    )
    assert "empty or invalid" in backup_config_module.describe_missing_backup_config(
        repo="library"
    )
