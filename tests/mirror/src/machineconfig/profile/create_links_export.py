from __future__ import annotations

import pytest
import typer

from machineconfig.profile import create_links as create_links_module
from machineconfig.profile import create_links_export as create_links_export_module


def _build_mapper_entry(file_name: str) -> create_links_module.ConfigMapper:
    return {
        "file_name": file_name,
        "config_file_default_path": f"/tmp/{file_name}",
        "config_file_self_managed_path": f"CONFIG_ROOT/{file_name}",
        "contents": False,
        "copy": False,
        "os": ["linux"],
    }


def test_main_from_parser_maps_aliases_and_dispatches_selected_items(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_call: dict[str, object] = {}

    def fake_read_mapper(repo: create_links_module.RepoLoose) -> create_links_module.MapperFileData:
        assert repo == "library"
        return {
            "public": {
                "git": [_build_mapper_entry("gitconfig")],
                "shell": [_build_mapper_entry("bashrc")],
                "unused": [_build_mapper_entry("unused")],
            },
            "private": {"ssh": [_build_mapper_entry("ssh_config")]},
        }

    def fake_apply_mapper(
        *,
        mapper_data: dict[str, list[create_links_module.ConfigMapper]],
        on_conflict: create_links_export_module.ON_CONFLICT_STRICT,
        method: create_links_export_module.METHOD_STRICT,
        direction: create_links_export_module.DIRECTION_STRICT,
    ) -> None:
        captured_call["mapper_data"] = mapper_data
        captured_call["on_conflict"] = on_conflict
        captured_call["method"] = method
        captured_call["direction"] = direction

    monkeypatch.setattr(create_links_module, "read_mapper", fake_read_mapper)
    monkeypatch.setattr(create_links_module, "apply_mapper", fake_apply_mapper)

    create_links_export_module.main_from_parser(direction="d", sensitivity="b", method="c", repo="l", on_conflict="os", which="git,shell")

    mapper_data = captured_call["mapper_data"]
    assert isinstance(mapper_data, dict)
    assert list(mapper_data) == ["git", "shell"]
    assert captured_call["on_conflict"] == "overwrite-self-managed"
    assert captured_call["method"] == "copy"
    assert captured_call["direction"] == "down"


def test_main_from_parser_exits_when_no_valid_items_are_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_read_mapper(_repo: create_links_module.RepoLoose) -> create_links_module.MapperFileData:
        return {"public": {"git": [_build_mapper_entry("gitconfig")]}, "private": {}}

    monkeypatch.setattr(create_links_module, "read_mapper", fake_read_mapper)

    with pytest.raises(typer.Exit) as exc_info:
        create_links_export_module.main_from_parser(
            direction="u", sensitivity="public", method="symlink", repo="library", on_conflict="throw-error", which="missing"
        )

    assert exc_info.value.exit_code == 1
