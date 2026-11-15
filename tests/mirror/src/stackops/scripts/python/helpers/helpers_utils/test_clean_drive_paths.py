from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog import CATALOG
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import PathCleanup
from stackops.scripts.python.helpers.helpers_utils.clean_drive_paths import removal_block_reason


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home" / "user"
    (home / ".cache" / "pip").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    for name in ("XDG_CACHE_HOME", "CARGO_HOME", "GRADLE_USER_HOME", "HF_HOME"):
        monkeypatch.delenv(name, raising=False)
    return home


def test_guard_refuses_home_its_ancestors_and_base_directories(fake_home: Path) -> None:
    assert removal_block_reason(fake_home) is not None
    assert removal_block_reason(fake_home.parent) is not None
    assert removal_block_reason(Path("/")) is not None
    assert removal_block_reason(Path("/var")) is not None
    assert removal_block_reason(fake_home / ".cache") is not None
    assert removal_block_reason(fake_home / ".cache" / "pip") is None


def test_catalog_globs_stay_inside_a_named_subfolder_of_their_anchor() -> None:
    globs = [
        path_glob
        for target in CATALOG for action in target.actions.values() if isinstance(action, PathCleanup)
        for path_glob in action.globs
    ]
    assert globs
    for path_glob in globs:
        parts = Path(path_glob.pattern).parts
        assert parts and not Path(path_glob.pattern).is_absolute() and ".." not in parts and "." not in parts, path_glob
        first_is_literal = not any(character in parts[0] for character in "*?[")
        assert first_is_literal or path_glob.anchor == "temp", path_glob
