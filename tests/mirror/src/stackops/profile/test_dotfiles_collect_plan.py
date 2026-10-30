import os
from pathlib import Path

import pytest

from stackops.profile.dotfiles_collect_plan import CollectVerdict, plan_collect, select_entries_to_record
from stackops.profile.dotfiles_mapper import MapperDocument, RawMapperEntry


def _entry(original: Path, managed: Path, contents: bool) -> RawMapperEntry:
    entry: RawMapperEntry = {"original": str(original), "self_managed": str(managed), "os": ["linux", "darwin", "windows"]}
    if contents:
        entry["contents"] = True
    return entry


def _verdicts(catalog: MapperDocument, user_mapper: MapperDocument, library_mapper: MapperDocument) -> dict[tuple[str, str], CollectVerdict]:
    plans = plan_collect(catalog=catalog, user_mapper=user_mapper, library_mapper=library_mapper, current_os="linux")
    return {(plan.group, plan.name): plan.verdict for plan in plans}


def test_single_path_states(tmp_path: Path) -> None:
    home, managed = tmp_path.joinpath("home"), tmp_path.joinpath("dotfiles")
    home.mkdir()
    managed.mkdir()
    home.joinpath("fresh").write_text("a", encoding="utf-8")
    home.joinpath("both").write_text("a", encoding="utf-8")
    managed.joinpath("both").write_text("b", encoding="utf-8")
    managed.joinpath("linked").write_text("a", encoding="utf-8")
    home.joinpath("linked").symlink_to(managed.joinpath("linked"))
    tmp_path.joinpath("elsewhere").write_text("a", encoding="utf-8")
    home.joinpath("own").symlink_to(tmp_path.joinpath("elsewhere"))
    managed.joinpath("stored").write_text("a", encoding="utf-8")
    names = ("fresh", "both", "linked", "own", "stored", "absent")
    catalog: MapperDocument = {"app": {name: _entry(home.joinpath(name), managed.joinpath(name), contents=False) for name in names}}

    assert _verdicts(catalog, {}, {}) == {
        ("app", "fresh"): "collect",
        ("app", "both"): "managed_path_exists",
        ("app", "linked"): "linked",
        ("app", "own"): "own_link",
        ("app", "stored"): "stored",
        ("app", "absent"): "absent",
    }


def test_contents_states(tmp_path: Path) -> None:
    managed = tmp_path.joinpath("dotfiles")
    partly_linked, own, flat = tmp_path.joinpath("partly_linked"), tmp_path.joinpath("own"), tmp_path.joinpath("flat")
    partly_linked.mkdir()
    own.mkdir()
    managed.joinpath("partly_linked").mkdir(parents=True)
    managed.joinpath("partly_linked", "id_a").write_text("a", encoding="utf-8")
    partly_linked.joinpath("id_a").symlink_to(managed.joinpath("partly_linked", "id_a"))
    partly_linked.joinpath("id_b").write_text("b", encoding="utf-8")
    tmp_path.joinpath("elsewhere").write_text("a", encoding="utf-8")
    own.joinpath("config").symlink_to(tmp_path.joinpath("elsewhere"))
    flat.write_text("a", encoding="utf-8")
    catalog: MapperDocument = {
        name: {"keys": _entry(tmp_path.joinpath(name), managed.joinpath(name), contents=True)} for name in ("partly_linked", "own", "flat")
    }

    assert _verdicts(catalog, {}, {}) == {
        ("partly_linked", "keys"): "collect",
        ("own", "keys"): "own_link",
        ("flat", "keys"): "not_a_directory",
    }


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs a non-root POSIX user to hit permission errors")
def test_unreadable_original(tmp_path: Path) -> None:
    locked = tmp_path.joinpath("locked")
    locked.mkdir()
    catalog: MapperDocument = {"app": {"config": _entry(locked.joinpath("config"), tmp_path.joinpath("dotfiles", "config"), contents=False)}}
    locked.chmod(0o000)
    try:
        assert _verdicts(catalog, {}, {}) == {("app", "config"): "unreadable"}
    finally:
        locked.chmod(0o700)


def test_existing_mappers_take_precedence(tmp_path: Path) -> None:
    home, managed = tmp_path.joinpath("home"), tmp_path.joinpath("dotfiles")
    home.joinpath(".ssh").mkdir(parents=True)
    for name in ("token", "rc", "conf"):
        home.joinpath(name).write_text("a", encoding="utf-8")
    known_entry = _entry(home.joinpath("token"), managed.joinpath("token"), contents=False)
    catalog: MapperDocument = {
        "ssh": {"keys": _entry(home.joinpath(".ssh"), managed.joinpath(".ssh"), contents=True)},
        "tool": {"token": known_entry, "rc": _entry(home.joinpath("rc"), managed.joinpath("rc"), contents=False)},
        "mine": {"conf": _entry(home.joinpath("conf"), managed.joinpath("conf"), contents=False)},
        "taken": {"conf": _entry(home.joinpath("conf2"), managed.joinpath("shared", "conf2"), contents=False)},
    }
    user_mapper: MapperDocument = {
        "keys": {"config": _entry(home.joinpath(".ssh", "config"), tmp_path.joinpath("elsewhere"), contents=False)},
        "tool": {"token": known_entry},
        "mine": {"conf": _entry(home.joinpath("conf"), managed.joinpath("my_conf"), contents=False)},
    }
    library_mapper: MapperDocument = {"settings": {"shared": _entry(tmp_path.joinpath("x"), managed.joinpath("shared"), contents=False)}}

    assert _verdicts(catalog, user_mapper, library_mapper) == {
        ("ssh", "keys"): "original_mapped",
        ("tool", "token"): "recorded",
        ("tool", "rc"): "collect",
        ("mine", "conf"): "user_group",
        ("taken", "conf"): "managed_path_mapped",
    }


def test_records_successes_and_their_other_os_siblings(tmp_path: Path) -> None:
    home, managed = tmp_path.joinpath("home"), tmp_path.joinpath("dotfiles")
    home.mkdir()
    for name in ("conf", "failed_conf"):
        home.joinpath(name).write_text("a", encoding="utf-8")
    windows_sibling: RawMapperEntry = {"original": "C:/conf", "self_managed": str(managed.joinpath("conf")), "os": ["windows"]}
    windows_only: RawMapperEntry = {"original": "C:/other", "self_managed": str(managed.joinpath("other")), "os": ["windows"]}
    catalog: MapperDocument = {
        "tool": {"unix": _entry(home.joinpath("conf"), managed.joinpath("conf"), contents=False), "windows": windows_sibling, "windows_only": windows_only},
        "broken": {"unix": _entry(home.joinpath("failed_conf"), managed.joinpath("failed_conf"), contents=False), "windows": windows_sibling},
    }
    plans = plan_collect(catalog=catalog, user_mapper={}, library_mapper={}, current_os="linux")

    assert select_entries_to_record(plans=plans, succeeded={("tool", "unix")}) == {"tool": {"unix": catalog["tool"]["unix"], "windows": windows_sibling}}
