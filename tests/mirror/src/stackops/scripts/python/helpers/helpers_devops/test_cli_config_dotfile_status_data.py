from pathlib import Path

import pytest

import stackops.utils.source_of_truth as source_of_truth
from stackops.profile.dotfiles_mapper import MapperDocument, write_dotfiles_mapper
from stackops.scripts.python.helpers.helpers_devops import cli_config_dotfile_status_data as status_data


def test_status_counts_sync_and_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, dotfiles, config = tmp_path.joinpath("home"), tmp_path.joinpath("dotfiles"), tmp_path.joinpath("config")
    stored_root = dotfiles.joinpath("stackops", "mapper", "files")
    stored_root.mkdir(parents=True)
    home.mkdir()
    config.mkdir()
    dotfiles.joinpath("settings", "app").mkdir(parents=True)
    dotfiles.joinpath("settings", "app", "config").write_text("mine", encoding="utf-8")
    home.joinpath(".app").symlink_to(dotfiles.joinpath("settings", "app", "config"))
    stored_root.joinpath("abc.rc").write_text("rc", encoding="utf-8")
    stored_root.joinpath("def.orphan").write_text("orphan", encoding="utf-8")
    config.joinpath("outside.conf").write_text("outside", encoding="utf-8")
    library_mapper: MapperDocument = {
        "app": {
            "config": {"original": str(home.joinpath(".app")), "self_managed": "CONFIG_ROOT/settings/app/config", "os": ["linux", "darwin", "windows"]},
            "theme": {"original": str(home.joinpath(".theme")), "self_managed": "CONFIG_ROOT/settings/app/theme", "os": ["linux"]},
        }
    }
    user_mapper: MapperDocument = {
        "app": {"config": {"original": str(home.joinpath(".app")), "self_managed": "DOTFILES_ROOT/settings/app/config", "os": ["linux", "darwin", "windows"]}},
        "mine": {
            "rc": {"original": str(home.joinpath(".rc")), "self_managed": "DOTFILES_ROOT/stackops/mapper/files/abc.rc", "os": ["linux"]},
            "rc_darwin": {"original": str(home.joinpath(".rc")), "self_managed": "DOTFILES_ROOT/stackops/mapper/files/abc.rc", "os": ["darwin"]},
            "outside": {"original": str(home.joinpath(".outside")), "self_managed": "CONFIG_ROOT/outside.conf", "os": ["linux"]},
        },
    }
    paths = {name: tmp_path.joinpath(f"""{name}.yaml""") for name in ("library", "example", "user")}
    for name, mapper in (("library", library_mapper), ("example", {}), ("user", user_mapper)):
        write_dotfiles_mapper(path=paths[name], mapper=mapper, header="")
    monkeypatch.setitem(source_of_truth.SOURCE_OF_TRUTH_PATH_TOKENS, "CONFIG_ROOT", config)
    monkeypatch.setitem(source_of_truth.SOURCE_OF_TRUTH_PATH_TOKENS, "DOTFILES_ROOT", dotfiles)
    monkeypatch.setattr(status_data, "LIBRARY_MAPPER_PATH", paths["library"])
    monkeypatch.setattr(status_data, "USER_EXAMPLE_MAPPER_PATH", paths["example"])
    monkeypatch.setattr(status_data, "USER_MAPPER_PATH", paths["user"])
    monkeypatch.setattr(status_data, "DOTFILES_ROOT", dotfiles)
    monkeypatch.setattr(status_data, "DOTFILES_MAPPER_FILES_ROOT", stored_root)

    loaded_mappers = status_data.load_mappers()
    mappers = status_data.collect_mappers_status(loaded_mappers, None)
    sync = status_data.collect_sync_status(loaded_mappers, None, "linux")
    radar = status_data.collect_radar_status(loaded_mappers, None, "linux")
    storage = status_data.collect_storage_status(loaded_mappers, None)

    assert mappers.user_counts == status_data.MapperCounts(groups=2, entries=4, entries_per_os={"linux": 3, "darwin": 2, "windows": 1})
    assert mappers.user_group_counts["mine"] == status_data.MapperCounts(groups=1, entries=3, entries_per_os={"linux": 2, "darwin": 1, "windows": 0})
    assert mappers.replaced_library_entries == [("app", "config")]
    assert {(item.program, item.file_name): item.status for item in sync.user} == {
        ("app", "config"): "Configured",
        ("mine", "rc"): "Missing default path",
        ("mine", "outside"): "Missing default path",
    }
    assert [(item.program, item.file_name) for item in sync.library] == [("app", "theme")]
    assert {(plan.group, plan.name): plan.verdict for plan in radar if plan.group == "app"} == {("app", "config"): "recorded", ("app", "theme"): "absent"}
    assert storage.dotfiles_root_footprint == status_data.Footprint(files=3, size_bytes=12)
    assert [(copy.path, copy.entries, copy.footprint) for copy in storage.managed_copies] == [
        (config.joinpath("outside.conf"), [("mine", "outside")], status_data.Footprint(files=1, size_bytes=7)),
        (dotfiles.joinpath("settings", "app", "config"), [("app", "config")], status_data.Footprint(files=1, size_bytes=4)),
        (stored_root.joinpath("abc.rc"), [("mine", "rc"), ("mine", "rc_darwin")], status_data.Footprint(files=1, size_bytes=2)),
    ]
    assert storage.managed_footprint == status_data.Footprint(files=3, size_bytes=13)
    assert storage.outside_dotfiles_root == [("mine", "outside", config.joinpath("outside.conf"))]
    assert storage.unreferenced_stored_paths == [stored_root.joinpath("def.orphan")]

    app_only = frozenset({"app"})
    filtered_storage = status_data.collect_storage_status(loaded_mappers, app_only)
    assert status_data.collect_mappers_status(loaded_mappers, app_only).user_counts == status_data.MapperCounts(
        groups=1, entries=1, entries_per_os={"linux": 1, "darwin": 1, "windows": 1}
    )
    assert [(item.program, item.file_name) for item in status_data.collect_sync_status(loaded_mappers, app_only, "linux").user] == [("app", "config")]
    assert {plan.group for plan in status_data.collect_radar_status(loaded_mappers, app_only, "linux")} == {"app"}
    assert [copy.path for copy in filtered_storage.managed_copies] == [dotfiles.joinpath("settings", "app", "config")]
    assert filtered_storage.outside_dotfiles_root == []
    assert filtered_storage.unreferenced_stored_paths == [stored_root.joinpath("def.orphan")]
