# pyright: reportPrivateUsage=false

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import subprocess
import zipfile

import pytest

from machineconfig.utils import path_extended as legacy
from machineconfig.utils import path_extended_functional as functional
from machineconfig.utils.path_extended import PathExtended
from tests.path_extended_functional_support import assert_matching_outcomes, capture_call


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz: object | None = None) -> FixedDatetime:
        _ = tz
        return cls(2024, 6, 7, 8, 9, 10, 111213)


def test_validate_name_and_timestamp_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(legacy, "datetime", FixedDatetime)
    monkeypatch.setattr(functional, "datetime", FixedDatetime)

    assert functional.validate_name("bad / name?.txt", replace="-") == legacy.validate_name("bad / name?.txt", replace="-")
    assert functional.timestamp(fmt="%Y%m%d-%H%M%S", name="report") == legacy.timestamp(fmt="%Y%m%d-%H%M%S", name="report")


def test_dunder_helpers_match(tmp_path: Path) -> None:
    base_path = tmp_path / "alpha" / "beta" / "gamma.txt"
    base_path.parent.mkdir(parents=True)
    base_path.write_text("payload", encoding="utf-8")
    original_path = PathExtended(base_path)
    plain_path = Path(base_path)

    assert_matching_outcomes(capture_call(lambda: original_path.__deepcopy__()), capture_call(lambda: functional.__deepcopy__(plain_path)))
    assert_matching_outcomes(capture_call(original_path.__getstate__), capture_call(lambda: functional.__getstate__(plain_path)))
    assert_matching_outcomes(capture_call(lambda: original_path + ".bak"), capture_call(lambda: functional.__add__(plain_path, ".bak")))
    assert_matching_outcomes(capture_call(lambda: "backup_" + original_path), capture_call(lambda: functional.__radd__(plain_path, "backup_")))
    assert_matching_outcomes(capture_call(lambda: original_path - tmp_path), capture_call(lambda: functional.__sub__(plain_path, tmp_path)))
    assert_matching_outcomes(capture_call(lambda: original_path.__getitem__(0)), capture_call(lambda: functional.__getitem__(plain_path, 0)))
    assert_matching_outcomes(capture_call(lambda: original_path.__getitem__([1, 2])), capture_call(lambda: functional.__getitem__(plain_path, [1, 2])))
    assert_matching_outcomes(capture_call(lambda: original_path.__getitem__(slice(1, None))), capture_call(lambda: functional.__getitem__(plain_path, slice(1, None))))


def test_setitem_matches_resulting_path_string(tmp_path: Path) -> None:
    original_path = PathExtended(tmp_path / "one" / "two" / "three.txt")
    functional_path = Path(tmp_path / "one" / "two" / "three.txt")

    original_path.__setitem__(1, "replacement")
    functional_result = functional.__setitem__(functional_path, 1, "replacement")

    assert str(functional_result) == str(original_path)


def test_repr_and_type_match(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    symlink_path = tmp_path / "file-link.txt"
    symlink_path.symlink_to(file_path)
    broken_link = tmp_path / "missing-link.txt"
    broken_link.symlink_to(tmp_path / "missing.txt")

    relative_missing = Path("relative-missing.txt")

    assert functional.__repr__(Path(file_path)) == PathExtended(file_path).__repr__()
    assert functional.__repr__(Path(symlink_path)) == PathExtended(symlink_path).__repr__()
    assert functional.__repr__(Path(broken_link)) == PathExtended(broken_link).__repr__()
    assert functional.__repr__(relative_missing) == PathExtended(relative_missing).__repr__()
    assert functional._type(relative_missing) == PathExtended(relative_missing)._type()


def test_path_shape_helpers_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", home_path.as_posix())

    nested = home_path / "docs" / "report.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("12345", encoding="utf-8")

    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("inner.txt", "zip-payload")

    assert_matching_outcomes(capture_call(lambda: PathExtended(nested).resolve(strict=False)), capture_call(lambda: functional.resolve(nested)))
    assert_matching_outcomes(capture_call(lambda: PathExtended(nested).rel2home()), capture_call(lambda: functional.rel2home(nested)))
    assert_matching_outcomes(capture_call(lambda: PathExtended(nested).collapseuser()), capture_call(lambda: functional.collapseuser(nested)))
    assert_matching_outcomes(capture_call(lambda: PathExtended(nested).split(at="docs", sep=1)), capture_call(lambda: functional.split(nested, at="docs", sep=1)))
    assert_matching_outcomes(capture_call(lambda: PathExtended(nested).size("b")), capture_call(lambda: functional.size(nested, "b")))
    assert_matching_outcomes(capture_call(lambda: PathExtended(nested).clickable()), capture_call(lambda: functional.clickable(nested)))
    assert_matching_outcomes(capture_call(lambda: PathExtended("https:/example.com/x").as_url_str()), capture_call(lambda: functional.as_url_str(Path("https:/example.com/x"))))
    assert_matching_outcomes(capture_call(lambda: PathExtended(archive_path).as_zip_path()), capture_call(lambda: functional.as_zip_path(archive_path)))


def test_run_shell_command_and_is_user_admin_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        _ = kwargs
        return subprocess.CompletedProcess(args=command, returncode=17, stdout="out", stderr="err")

    monkeypatch.setattr(legacy.subprocess, "run", fake_run)
    monkeypatch.setattr(functional.subprocess, "run", fake_run)
    monkeypatch.setattr(legacy.os, "getuid", lambda: 123)
    monkeypatch.setattr(functional.os, "getuid", lambda: 123)

    assert legacy._is_user_admin() is functional._is_user_admin()
    assert_matching_outcomes(
        capture_call(lambda: legacy._run_shell_command("printf hi", "bash", check=True)),
        capture_call(lambda: functional._run_shell_command("printf hi", "bash", check=True)),
    )


def test_search_matches_across_common_modes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "visible.txt").write_text("v", encoding="utf-8")
    (workspace / ".hidden.txt").write_text("h", encoding="utf-8")
    folder = workspace / "folder2"
    folder.mkdir()
    (folder / "nested10.txt").write_text("10", encoding="utf-8")
    (folder / "nested2.txt").write_text("2", encoding="utf-8")
    compressed_zip = workspace / "compressed.zip"
    with zipfile.ZipFile(compressed_zip, "w") as archive:
        archive.writestr("archive/a.txt", "inside")
        archive.writestr("archive/b.md", "inside-md")

    original_path = PathExtended(workspace)
    functional_path = Path(workspace)

    search_cases = [
        (
            lambda path: path.search(pattern="*.txt", r=True, files=True, folders=False, win_order=True),
            lambda path: functional.search(path, pattern="*.txt", r=True, files=True, folders=False, win_order=True),
        ),
        (
            lambda path: path.search(pattern="*.txt", r=False, dotfiles=True, files=True, folders=False),
            lambda path: functional.search(path, pattern="*.txt", r=False, dotfiles=True, files=True, folders=False),
        ),
        (
            lambda path: PathExtended(compressed_zip).search(pattern="*.txt", r=True, compressed=True, files=True, folders=False),
            lambda path: functional.search(compressed_zip, pattern="*.txt", r=True, compressed=True, files=True, folders=False),
        ),
        (
            lambda path: path.search(pattern="*", r=True, files=False, folders=True, not_in=["archive"]),
            lambda path: functional.search(path, pattern="*", r=True, files=False, folders=True, not_in=["archive"]),
        ),
    ]

    for original_case, functional_case in search_cases:
        original_items = original_case(original_path)
        functional_items = functional_case(functional_path)
        original_normalized = [str(item) if isinstance(item, Path) else f"{item.root.filename}::{item.at}" for item in original_items]
        functional_normalized = [str(item) if isinstance(item, Path) else f"{item.root.filename}::{item.at}" for item in functional_items]
        assert functional_normalized == original_normalized


def test_tmp_helpers_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_path = tmp_path / "home"
    home_path.mkdir()
    monkeypatch.setenv("HOME", home_path.as_posix())
    monkeypatch.setattr(legacy, "randstr", lambda noun=False: "fixed")  # noqa: ARG005
    monkeypatch.setattr(functional, "randstr", lambda noun=False: "fixed")  # noqa: ARG005
    monkeypatch.setattr(legacy, "timestamp", lambda fmt=None, name=None: "stamp")  # noqa: ARG005
    monkeypatch.setattr(functional, "timestamp", lambda fmt=None, name=None: "stamp")  # noqa: ARG005

    assert_matching_outcomes(capture_call(lambda: PathExtended.tmp(folder="area", file="demo.txt", root="~/tmp_results")), capture_call(lambda: functional.tmp(folder="area", file="demo.txt", root="~/tmp_results")))
    assert_matching_outcomes(capture_call(lambda: PathExtended.tmpdir(prefix="cache")), capture_call(lambda: functional.tmpdir(prefix="cache")))
    assert_matching_outcomes(capture_call(lambda: PathExtended.tmpfile(name="report", suffix=".txt", folder="exports", tstamp=True)), capture_call(lambda: functional.tmpfile(name="report", suffix=".txt", folder="exports", tstamp=True)))


def test_resolve_path_matches(tmp_path: Path) -> None:
    source = tmp_path / "folder" / "item.txt"
    source.parent.mkdir(parents=True)
    source.write_text("x", encoding="utf-8")

    original_path = PathExtended(source)
    functional_path = Path(source)

    assert_matching_outcomes(
        capture_call(lambda: original_path._resolve_path(folder="../target", name="copied.txt", path=None, default_name=source.name, rel2it=True)),
        capture_call(lambda: functional._resolve_path(functional_path, folder="../target", name="copied.txt", target_path=None, default_name=source.name, rel2it=True)),
        original_root=tmp_path,
        functional_root=tmp_path,
    )
    assert_matching_outcomes(
        capture_call(lambda: original_path._resolve_path(folder=None, name=None, path=tmp_path / "alt.txt", default_name=source.name, rel2it=False)),
        capture_call(lambda: functional._resolve_path(functional_path, folder=None, name=None, target_path=tmp_path / "alt.txt", default_name=source.name, rel2it=False)),
        original_root=tmp_path,
        functional_root=tmp_path,
    )
