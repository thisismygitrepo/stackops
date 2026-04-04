from pathlib import Path
from unittest.mock import call, patch

import pytest
import yaml
from typer.testing import CliRunner

from machineconfig.profile import create_links
from machineconfig.profile.dotfiles_mapper import OsField
from machineconfig.scripts.python import devops as devops_cli
from machineconfig.scripts.python.helpers.helpers_devops import cli_config, cli_config_dotfile


runner = CliRunner()
ALL_DOTFILE_OS: OsField = ["linux", "darwin", "windows"]


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
                    "config_file_self_managed_path": "~/dotfiles/demo",
                    "contents": None,
                    "copy": None,
                    "os": ALL_DOTFILE_OS,
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


def test_copy_assets_all_copies_scripts_and_settings() -> None:
    with patch("machineconfig.profile.create_helper.copy_assets_to_machine") as copy_assets_to_machine:
        result = runner.invoke(cli_config.get_app(), ["copy-assets", "all"])

    assert result.exit_code == 0
    assert copy_assets_to_machine.call_args_list == [
        call(which="scripts"),
        call(which="settings"),
    ]


def test_copy_assets_rejects_legacy_both_argument() -> None:
    result = runner.invoke(cli_config.get_app(), ["copy-assets", "both"])

    assert result.exit_code != 0
    assert "Invalid value" in result.output
    assert "both" in result.output


def test_read_mapper_loads_yaml_file(tmp_path: Path) -> None:
    mapper_path = tmp_path / "mapper_dotfiles.yaml"
    mapper_path.write_text(
        f"""
demo_public:
  config:
    original: ~/.demo-public
    self_managed: CONFIG_ROOT/settings/demo/public.conf
    os:
    - {create_links.SYSTEM}
demo_private:
  creds:
    original: ~/.demo-private
    self_managed: ~/dotfiles/demo/private.conf
    os:
    - linux
    - darwin
    - windows
""".lstrip(),
        encoding="utf-8",
    )

    with patch.object(create_links, "LIBRARY_MAPPER_PATH", mapper_path):
        mapper = create_links.read_mapper(repo="library")

    assert mapper["public"] == {
        "demo_public": [
            {
                "file_name": "config",
                "config_file_default_path": "~/.demo-public",
                "config_file_self_managed_path": "CONFIG_ROOT/settings/demo/public.conf",
                "contents": None,
                "copy": None,
                "os": [create_links.SYSTEM],
            }
        ]
    }
    assert mapper["private"] == {
        "demo_private": [
            {
                "file_name": "creds",
                "config_file_default_path": "~/.demo-private",
                "config_file_self_managed_path": "~/dotfiles/demo/private.conf",
                "contents": None,
                "copy": None,
                "os": ALL_DOTFILE_OS,
            }
        ]
    }


def test_read_mapper_rejects_scalar_os_field(tmp_path: Path) -> None:
    mapper_path = tmp_path / "mapper_dotfiles.yaml"
    mapper_path.write_text(
        """
demo:
  config:
    original: ~/.demo
    self_managed: ~/dotfiles/demo
    os: windows
""".lstrip(),
        encoding="utf-8",
    )

    with (
        patch.object(create_links, "LIBRARY_MAPPER_PATH", mapper_path),
        pytest.raises(TypeError, match="must be a YAML list\\[str\\]"),
    ):
        create_links.read_mapper(repo="library")


def test_record_mapping_writes_yaml_mapper_file(tmp_path: Path) -> None:
    mapper_path = tmp_path / "mapper_dotfiles.yaml"
    original_path = tmp_path / "demo-file.conf"
    managed_path = tmp_path / "managed" / "demo-file.conf"

    with patch.object(cli_config_dotfile, "USER_MAPPER_PATH", mapper_path):
        cli_config_dotfile.record_mapping(
            orig_path=original_path,
            new_path=managed_path,
            method="copy",
            section="demo",
            os_filter="linux,darwin",
        )

    mapper_data = yaml.safe_load(mapper_path.read_text(encoding="utf-8"))
    assert mapper_data == {
        "demo": {
            "demo_file": {
                "original": original_path.as_posix(),
                "self_managed": managed_path.as_posix(),
                "copy": True,
                "os": ["linux", "darwin"],
            }
        }
    }


def test_record_mapping_rejects_invalid_os_filter(tmp_path: Path) -> None:
    mapper_path = tmp_path / "mapper_dotfiles.yaml"
    original_path = tmp_path / "demo-file.conf"
    managed_path = tmp_path / "managed" / "demo-file.conf"

    with (
        patch.object(cli_config_dotfile, "USER_MAPPER_PATH", mapper_path),
        pytest.raises(ValueError, match="must be one of"),
    ):
        cli_config_dotfile.record_mapping(
            orig_path=original_path,
            new_path=managed_path,
            method="copy",
            section="demo",
            os_filter="plan9",
        )


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
        "config_file_self_managed_path": str(managed_path),
        "contents": None,
        "copy": None,
        "os": ALL_DOTFILE_OS,
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
