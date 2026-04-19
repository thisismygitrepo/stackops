

from pathlib import Path

import pytest

from stackops.cluster.sessions_managers.windows_terminal.wt_utils import manager_persistence as persistence_module


def test_generate_session_id_has_expected_shape() -> None:
    session_id = persistence_module.generate_session_id()

    assert len(session_id) == 8
    assert "-" not in session_id


def test_save_and_load_json_round_trip(tmp_path: Path) -> None:
    file_path = tmp_path / "nested" / "data.json"
    data: dict[str, object] = {
        "name": "session-a",
        "count": 2,
    }

    persistence_module.ensure_session_dir_exists(file_path.parent)
    persistence_module.save_json_file(file_path, data, "data")
    loaded = persistence_module.load_json_file(file_path, "data")

    assert file_path.is_file()
    assert loaded == data


def test_load_json_file_raises_when_file_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing"):
        persistence_module.load_json_file(tmp_path / "missing.json", "missing")


def test_list_saved_sessions_and_delete_session_dir(tmp_path: Path) -> None:
    saved_a = tmp_path / "sess-a"
    saved_b = tmp_path / "sess-b"
    ignored = tmp_path / "ignored"
    persistence_module.ensure_session_dir_exists(saved_a)
    persistence_module.ensure_session_dir_exists(saved_b)
    persistence_module.ensure_session_dir_exists(ignored)
    (saved_a / "metadata.json").write_text("{}", encoding="utf-8")
    (saved_b / "metadata.json").write_text("{}", encoding="utf-8")

    listed = persistence_module.list_saved_sessions_in_dir(tmp_path)
    deleted = persistence_module.delete_session_dir(saved_a, "sess-a")
    missing_delete = persistence_module.delete_session_dir(tmp_path / "missing", "missing")

    assert listed == ["sess-a", "sess-b"]
    assert deleted is True
    assert not saved_a.exists()
    assert missing_delete is False
