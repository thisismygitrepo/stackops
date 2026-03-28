from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from machineconfig.profile import create_links
from machineconfig.scripts.python import devops as devops_cli
from machineconfig.scripts.python.helpers.helpers_devops import cli_config


runner = CliRunner()


def test_config_sync_help_exposes_direction_argument() -> None:
    result = runner.invoke(devops_cli.get_app(), ["config", "s", "--help"])

    assert result.exit_code == 0
    assert "DIRECTION" in result.output
    assert "Direction of sync" in result.output
    assert "up" in result.output
    assert "down" in result.output
    assert "--sensitivity" in result.output


def test_config_sync_passes_direction_without_copying_assets() -> None:
    mapper: create_links.MapperFileData = {
        "public": {
            "demo": [
                {
                    "file_name": "demo",
                    "config_file_default_path": "~/.demo",
                    "self_managed_config_file_path": "~/dotfiles/demo",
                    "contents": None,
                    "copy": None,
                    "os": "any",
                }
            ]
        },
        "private": {},
    }

    with (
        patch.object(create_links, "read_mapper", return_value=mapper) as read_mapper,
        patch.object(create_links, "apply_mapper") as apply_mapper,
        patch("machineconfig.profile.create_helper.copy_assets_to_machine") as copy_assets_to_machine,
    ):
        result = runner.invoke(
            cli_config.get_app(),
            ["sync", "down", "--sensitivity", "public", "--method", "copy", "--which", "all"],
        )

    assert result.exit_code == 0
    read_mapper.assert_called_once_with(repo="library")
    apply_mapper.assert_called_once_with(
        mapper_data=mapper["public"],
        on_conflict="throw-error",
        method="copy",
        direction="down",
    )
    copy_assets_to_machine.assert_not_called()


@pytest.mark.parametrize(
    ("direction", "default_value", "managed_value", "on_conflict", "expected_default", "expected_managed"),
    [
        ("up", "machine-default", None, "overwrite-self-managed", "machine-default", "machine-default"),
        ("down", "machine-default", "managed-backup", "overwrite-default-path", "managed-backup", "managed-backup"),
    ],
)
def test_apply_mapper_copy_respects_explicit_direction(
    tmp_path: Path,
    direction: create_links.DIRECTION_STRICT,
    default_value: str | None,
    managed_value: str | None,
    on_conflict: create_links.ON_CONFLICT_STRICT,
    expected_default: str,
    expected_managed: str,
) -> None:
    default_path = tmp_path / "default.txt"
    managed_path = tmp_path / "managed.txt"
    if default_value is not None:
        default_path.write_text(default_value, encoding="utf-8")
    if managed_value is not None:
        managed_path.write_text(managed_value, encoding="utf-8")
    mapper: create_links.ConfigMapper = {
        "file_name": "demo",
        "config_file_default_path": str(default_path),
        "self_managed_config_file_path": str(managed_path),
        "contents": None,
        "copy": None,
        "os": "any",
    }

    create_links.ERROR_LIST.clear()
    with patch.object(create_links, "CONFIG_ROOT", tmp_path / "config-root"):
        create_links.apply_mapper(
            mapper_data={"demo": [mapper]},
            on_conflict=on_conflict,
            method="copy",
            direction=direction,
        )

    assert default_path.read_text(encoding="utf-8") == expected_default
    assert managed_path.read_text(encoding="utf-8") == expected_managed
