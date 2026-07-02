from functools import partial
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from stackops.profile.dotfiles_mapper import OsName
from stackops.scripts.python.helpers.helpers_cloud.backup_config import BackupConfig, BackupItem, load_backup_config_file, write_backup_config
from stackops.scripts.python.helpers.helpers_devops import cli_data, cli_data_subset


def test_subset_cli_defaults_to_user_source_and_opens_picker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "user-data.yaml"
    output_path = tmp_path / "output.yaml"
    source_config: BackupConfig = {"group": {"item": _backup_item(path_local="~/item", os_values={"linux"})}}
    write_backup_config(source_path, source_config)
    picker_source_paths: list[Path] = []

    def choose_entry(*, config: BackupConfig, source_path: Path) -> list[cli_data_subset.BackupEntryKey]:
        assert config == source_config
        picker_source_paths.append(source_path)
        return [cli_data_subset.BackupEntryKey(group_name="group", item_name="item")]

    monkeypatch.setattr(cli_data_subset, "USER_BACKUP_PATH", source_path)
    monkeypatch.setattr(cli_data_subset, "_choose_subset_entry_keys", choose_entry)

    result = CliRunner().invoke(cli_data.get_app(), ["subset", str(output_path)])

    assert result.exit_code == 0
    assert picker_source_paths == [source_path]
    assert load_backup_config_file(output_path, empty_as_config=False) == source_config


def test_subset_data_file_writes_selected_entries_in_source_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "source.yaml"
    output_path = tmp_path / "nested" / "output.yaml"
    source_config: BackupConfig = {
        "alpha": {
            "one": _backup_item(path_local="~/alpha-one", os_values={"linux"}),
            "two": _backup_item(path_local="~/alpha-two", os_values={"darwin"}),
        },
        "beta": {"three": _backup_item(path_local="~/beta-three", os_values={"windows"})},
    }
    write_backup_config(source_path, source_config)
    monkeypatch.setattr(
        cli_data_subset,
        "_choose_subset_entry_keys",
        partial(
            _choose_subset_entry_keys,
            selected_keys=[
                cli_data_subset.BackupEntryKey(group_name="beta", item_name="three"),
                cli_data_subset.BackupEntryKey(group_name="alpha", item_name="two"),
            ],
        ),
    )

    cli_data_subset.subset_data_file(source_path=source_path, output_path=output_path, on_conflict="throw-error")

    output_config = load_backup_config_file(output_path, empty_as_config=False)
    assert output_config is not None
    assert list(output_config) == ["alpha", "beta"]
    assert list(output_config["alpha"]) == ["two"]
    assert list(output_config["beta"]) == ["three"]
    assert output_config["alpha"]["two"] == source_config["alpha"]["two"]
    assert output_config["beta"]["three"] == source_config["beta"]["three"]


def test_subset_data_file_append_merges_groups_without_replacing_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "source.yaml"
    output_path = tmp_path / "output.yaml"
    source_config: BackupConfig = {
        "shared": {"selected": _backup_item(path_local="~/selected", os_values={"linux"})},
        "new_group": {"new": _backup_item(path_local="~/new", os_values={"darwin"})},
    }
    existing_config: BackupConfig = {"shared": {"existing": _backup_item(path_local="~/existing", os_values={"windows"})}}
    write_backup_config(source_path, source_config)
    write_backup_config(output_path, existing_config)
    monkeypatch.setattr(
        cli_data_subset,
        "_choose_subset_entry_keys",
        partial(
            _choose_subset_entry_keys,
            selected_keys=[
                cli_data_subset.BackupEntryKey(group_name="shared", item_name="selected"),
                cli_data_subset.BackupEntryKey(group_name="new_group", item_name="new"),
            ],
        ),
    )

    cli_data_subset.subset_data_file(source_path=source_path, output_path=output_path, on_conflict="append")

    output_config = load_backup_config_file(output_path, empty_as_config=False)
    assert output_config is not None
    assert list(output_config["shared"]) == ["existing", "selected"]
    assert output_config["shared"]["existing"] == existing_config["shared"]["existing"]
    assert output_config["shared"]["selected"] == source_config["shared"]["selected"]
    assert output_config["new_group"]["new"] == source_config["new_group"]["new"]


def test_subset_data_file_append_refuses_duplicate_entry_without_mutating_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "source.yaml"
    output_path = tmp_path / "output.yaml"
    source_config: BackupConfig = {"shared": {"duplicate": _backup_item(path_local="~/source", os_values={"linux"})}}
    existing_config: BackupConfig = {"shared": {"duplicate": _backup_item(path_local="~/output", os_values={"linux"})}}
    write_backup_config(source_path, source_config)
    write_backup_config(output_path, existing_config)
    original_output = output_path.read_text(encoding="utf-8")
    monkeypatch.setattr(
        cli_data_subset,
        "_choose_subset_entry_keys",
        partial(_choose_subset_entry_keys, selected_keys=[cli_data_subset.BackupEntryKey(group_name="shared", item_name="duplicate")]),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_data_subset.subset_data_file(source_path=source_path, output_path=output_path, on_conflict="append")

    assert exc_info.value.exit_code == 1
    assert output_path.read_text(encoding="utf-8") == original_output


def test_subset_data_file_refuses_source_as_output(tmp_path: Path) -> None:
    source_path = tmp_path / "source.yaml"
    source_config: BackupConfig = {"group": {"item": _backup_item(path_local="~/item", os_values={"linux"})}}
    write_backup_config(source_path, source_config)
    original_source = source_path.read_text(encoding="utf-8")

    with pytest.raises(typer.Exit) as exc_info:
        cli_data_subset.subset_data_file(source_path=source_path, output_path=source_path, on_conflict="overwrite")

    assert exc_info.value.exit_code == 1
    assert source_path.read_text(encoding="utf-8") == original_source


def test_subset_data_file_empty_selection_does_not_create_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "source.yaml"
    output_path = tmp_path / "output.yaml"
    source_config: BackupConfig = {"group": {"item": _backup_item(path_local="~/item", os_values={"linux"})}}
    write_backup_config(source_path, source_config)
    monkeypatch.setattr(cli_data_subset, "_choose_subset_entry_keys", partial(_choose_subset_entry_keys, selected_keys=[]))

    with pytest.raises(typer.Exit) as exc_info:
        cli_data_subset.subset_data_file(source_path=source_path, output_path=output_path, on_conflict="throw-error")

    assert exc_info.value.exit_code == 1
    assert not output_path.exists()


def _backup_item(*, path_local: str, os_values: set[OsName]) -> BackupItem:
    return {"path_local": path_local, "path_cloud": "^", "share_url": None, "zip": False, "encryption": None, "rel2home": True, "os": os_values}


def _choose_subset_entry_keys(
    *, config: BackupConfig, source_path: Path, selected_keys: list[cli_data_subset.BackupEntryKey]
) -> list[cli_data_subset.BackupEntryKey]:
    assert config
    assert source_path.exists()
    return selected_keys
