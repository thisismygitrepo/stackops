from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from machineconfig.profile import create_links as create_links_module


PathPair = tuple[create_links_module.PathExtended, create_links_module.PathExtended]


def _call_iter_operation_paths(
    config_file_default_path: create_links_module.PathExtended,
    config_file_self_managed_path: create_links_module.PathExtended,
    contents: bool,
    direction: str,
) -> list[PathPair]:
    iter_operation_paths = cast(
        Callable[[create_links_module.PathExtended, create_links_module.PathExtended, bool, str], list[PathPair]],
        getattr(create_links_module, "_iter_operation_paths"),
    )
    return iter_operation_paths(config_file_default_path, config_file_self_managed_path, contents, direction)


def _call_run_directional_operation(
    config_file_default_path: create_links_module.PathExtended,
    config_file_self_managed_path: create_links_module.PathExtended,
    on_conflict: str,
    method: str,
    direction: str,
) -> dict[str, str]:
    run_directional_operation = cast(
        Callable[[create_links_module.PathExtended, create_links_module.PathExtended, str, str, str], dict[str, str]],
        getattr(create_links_module, "_run_directional_operation"),
    )
    return run_directional_operation(config_file_default_path, config_file_self_managed_path, on_conflict, method, direction)


def test_read_mapper_filters_current_os_and_splits_public_private_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    library_mapper_path = tmp_path / "library_mapper.yaml"
    config_root = tmp_path / "managed"

    def fake_load_dotfiles_mapper(_path: Path) -> dict[str, dict[str, dict[str, object]]]:
        return {
            "git": {
                "public_config": {
                    "original": str(tmp_path / "defaults" / "gitconfig"),
                    "self_managed": "CONFIG_ROOT/git/config",
                    "os": ["linux"],
                    "copy": True,
                },
                "private_config": {
                    "original": str(tmp_path / "defaults" / "ssh_config"),
                    "self_managed": str(tmp_path / "private" / "ssh_config"),
                    "os": ["linux"],
                },
                "windows_only": {"original": "C:/Users/alex/_gitconfig", "self_managed": "CONFIG_ROOT/windows/gitconfig", "os": ["windows"]},
            }
        }

    monkeypatch.setattr(create_links_module, "LIBRARY_MAPPER_PATH", library_mapper_path)
    monkeypatch.setattr(create_links_module, "CONFIG_ROOT", config_root)
    monkeypatch.setattr(create_links_module, "SYSTEM", "linux")
    monkeypatch.setattr(create_links_module, "load_dotfiles_mapper", fake_load_dotfiles_mapper)

    mapper_data = create_links_module.read_mapper(repo="library")

    assert list(mapper_data["public"]) == ["git"]
    assert list(mapper_data["private"]) == ["git"]
    assert [item["file_name"] for item in mapper_data["public"]["git"]] == ["public_config"]
    assert [item["file_name"] for item in mapper_data["private"]["git"]] == ["private_config"]


def test_iter_operation_paths_returns_sorted_children_for_contents_mapper(tmp_path: Path) -> None:
    default_dir = create_links_module.PathExtended(tmp_path / "default")
    managed_dir = create_links_module.PathExtended(tmp_path / "managed")
    default_dir.mkdir(parents=True)
    default_dir.joinpath("z-last.txt").write_text("z", encoding="utf-8")
    default_dir.joinpath("a-first.txt").write_text("a", encoding="utf-8")

    operation_paths = _call_iter_operation_paths(
        config_file_default_path=default_dir, config_file_self_managed_path=managed_dir, contents=True, direction="up"
    )

    assert operation_paths == [
        (default_dir.joinpath("a-first.txt"), managed_dir.joinpath("a-first.txt")),
        (default_dir.joinpath("z-last.txt"), managed_dir.joinpath("z-last.txt")),
    ]


def test_iter_operation_paths_rejects_non_directory_contents_sources(tmp_path: Path) -> None:
    default_file = create_links_module.PathExtended(tmp_path / "default.txt")
    managed_dir = create_links_module.PathExtended(tmp_path / "managed")
    default_file.write_text("payload", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="expects a directory"):
        _call_iter_operation_paths(config_file_default_path=default_file, config_file_self_managed_path=managed_dir, contents=True, direction="up")


def test_run_directional_operation_uses_expected_target_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    default_path = create_links_module.PathExtended(tmp_path / "default.txt")
    managed_path = create_links_module.PathExtended(tmp_path / "managed.txt")
    copy_calls: list[tuple[Path, Path, str]] = []
    symlink_calls: list[tuple[Path, Path, str]] = []

    def fake_copy_map(*, config_file_default_path: Path, config_file_self_managed_path: Path, on_conflict: str) -> dict[str, str]:
        copy_calls.append((config_file_default_path, config_file_self_managed_path, on_conflict))
        return {"action": "copied", "details": "ok"}

    def fake_symlink_map(*, config_file_default_path: Path, config_file_self_managed_path: Path, on_conflict: str) -> dict[str, str]:
        symlink_calls.append((config_file_default_path, config_file_self_managed_path, on_conflict))
        return {"action": "linked", "details": "ok"}

    monkeypatch.setattr(create_links_module, "copy_map", fake_copy_map)
    monkeypatch.setattr(create_links_module, "symlink_map", fake_symlink_map)

    up_result = _call_run_directional_operation(
        config_file_default_path=default_path,
        config_file_self_managed_path=managed_path,
        on_conflict="overwrite-self-managed",
        method="copy",
        direction="up",
    )
    down_result = _call_run_directional_operation(
        config_file_default_path=default_path,
        config_file_self_managed_path=managed_path,
        on_conflict="backup-self-managed",
        method="copy",
        direction="down",
    )
    symlink_result = _call_run_directional_operation(
        config_file_default_path=default_path,
        config_file_self_managed_path=managed_path,
        on_conflict="throw-error",
        method="symlink",
        direction="down",
    )

    assert up_result == {"action": "copied", "details": "ok"}
    assert down_result == {"action": "copied", "details": "ok"}
    assert symlink_result == {"action": "linked", "details": "ok"}
    assert copy_calls == [(managed_path, default_path, "overwrite-default-path"), (default_path, managed_path, "backup-self-managed")]
    assert symlink_calls == [(default_path, managed_path, "throw-error")]
