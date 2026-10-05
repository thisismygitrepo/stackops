from pathlib import Path
from typing import Literal

import pytest

from stackops.profile.create_links import ConfigMapper, MapperFileData
from stackops.scripts.python.helpers.helpers_devops import devops_status_config


def _mapping(default_path: Path, managed_path: Path, *, contents: bool, copy: bool) -> ConfigMapper:
    return {
        "file_name": managed_path.name,
        "config_file_default_path": str(default_path),
        "config_file_self_managed_path": str(managed_path),
        "contents": contents,
        "copy": copy,
        "os": ["linux"],
    }


def test_contents_mapping_requires_children_to_be_configured(tmp_path: Path) -> None:
    default_path = tmp_path.joinpath("default")
    managed_path = tmp_path.joinpath("managed")
    default_path.mkdir()
    managed_path.mkdir()
    managed_path.joinpath("config").write_text("managed", encoding="utf-8")
    default_path.joinpath("config").write_text("managed", encoding="utf-8")

    status = devops_status_config._check_config_file(
        "program", "private", _mapping(default_path, managed_path, contents=True, copy=False)
    )

    assert status.status == "Contents differ"
    assert not status.configured


def test_contents_mapping_accepts_child_links_and_extra_default_files(tmp_path: Path) -> None:
    default_path = tmp_path.joinpath("default")
    managed_path = tmp_path.joinpath("managed")
    default_path.mkdir()
    managed_path.mkdir()
    managed_path.joinpath("config").write_text("managed", encoding="utf-8")
    managed_path.joinpath("nested").mkdir()
    managed_path.joinpath("nested", "config").write_text("nested", encoding="utf-8")
    default_path.joinpath("config").symlink_to(managed_path.joinpath("config"))
    default_path.joinpath("nested").symlink_to(managed_path.joinpath("nested"), target_is_directory=True)
    default_path.joinpath("unmanaged").write_text("unmanaged", encoding="utf-8")

    status = devops_status_config._check_config_file(
        "program", "private", _mapping(default_path, managed_path, contents=True, copy=False)
    )

    assert status.status == "Configured"
    assert status.configured


@pytest.mark.parametrize("changed", [False, True])
def test_contents_copy_verifies_nested_children(tmp_path: Path, changed: bool) -> None:
    default_path = tmp_path.joinpath("default")
    managed_path = tmp_path.joinpath("managed")
    default_path.joinpath("nested").mkdir(parents=True)
    managed_path.joinpath("nested").mkdir(parents=True)
    managed_path.joinpath("nested", "config").write_text("managed", encoding="utf-8")
    default_path.joinpath("nested", "config").write_text("changed" if changed else "managed", encoding="utf-8")
    default_path.joinpath("unmanaged").write_text("unmanaged", encoding="utf-8")

    status = devops_status_config._check_config_file(
        "program", "private", _mapping(default_path, managed_path, contents=True, copy=True)
    )

    assert status.configured is not changed
    assert status.status == ("Contents differ" if changed else "Configured")


@pytest.mark.parametrize("difference", ["none", "content", "extra", "missing", "type", "empty directory"])
def test_directory_copy_verifies_structure_and_content(
    tmp_path: Path, difference: Literal["none", "content", "extra", "missing", "type", "empty directory"]
) -> None:
    default_path = tmp_path.joinpath("default")
    managed_path = tmp_path.joinpath("managed")
    default_path.joinpath("nested").mkdir(parents=True)
    managed_path.joinpath("nested").mkdir(parents=True)
    managed_path.joinpath("nested", "config").write_text("managed", encoding="utf-8")
    default_config = default_path.joinpath("nested", "config")
    default_config.write_text("managed", encoding="utf-8")
    match difference:
        case "content":
            default_config.write_text("changed", encoding="utf-8")
        case "extra":
            default_path.joinpath("extra").write_text("extra", encoding="utf-8")
        case "missing":
            default_config.unlink()
        case "type":
            default_config.unlink()
            default_config.mkdir()
        case "empty directory":
            managed_path.joinpath("empty").mkdir()
        case "none":
            pass

    status = devops_status_config._check_config_file(
        "program", "private", _mapping(default_path, managed_path, contents=False, copy=True)
    )

    assert status.configured is (difference == "none")
    assert status.status == ("Configured" if difference == "none" else "Copy differs")


def test_copy_accepts_existing_link_to_managed_path(tmp_path: Path) -> None:
    default_path = tmp_path.joinpath("default")
    managed_path = tmp_path.joinpath("managed")
    managed_path.mkdir()
    managed_path.joinpath("config").write_text("managed", encoding="utf-8")
    default_path.symlink_to(managed_path, target_is_directory=True)

    status = devops_status_config._check_config_file(
        "program", "private", _mapping(default_path, managed_path, contents=False, copy=True)
    )

    assert status.configured
    assert status.status == "Configured"


def test_config_status_counts_only_verified_mappings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_path = tmp_path.joinpath("default")
    managed_path = tmp_path.joinpath("managed")
    default_path.mkdir()
    managed_path.mkdir()
    managed_path.joinpath("config").write_text("managed", encoding="utf-8")
    mapper: MapperFileData = {
        "public": {},
        "private": {"program": [_mapping(default_path, managed_path, contents=True, copy=False)]},
    }
    monkeypatch.setattr(devops_status_config, "read_mapper", lambda *, source: mapper)

    status = devops_status_config.check_config_files_status()

    assert status["private_count"] == 1
    assert status["private_linked"] == 0
    assert not status["items"][0].configured
