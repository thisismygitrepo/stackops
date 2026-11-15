from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import ProjectCleanup, ProjectMarker
from stackops.scripts.python.helpers.helpers_utils.clean_drive_projects import find_project_entries


CLEANUPS: dict[str, ProjectCleanup] = {
    "ai-scratch": ProjectCleanup(directory_names=(".ai",), marker=None),
    "node-modules": ProjectCleanup(directory_names=("node_modules",), marker=ProjectMarker(relation="sibling", name="package.json")),
    "python-venvs": ProjectCleanup(directory_names=(".venv",), marker=ProjectMarker(relation="child", name="pyvenv.cfg")),
    "python-tool-caches": ProjectCleanup(directory_names=("__pycache__",), marker=None),
}


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_finder_honours_markers_and_never_enters_hidden_or_dependency_folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _touch(tmp_path / "web" / "package.json")
    _touch(tmp_path / "web" / "node_modules" / "dep" / "package.json")
    _touch(tmp_path / "web" / "node_modules" / "dep" / "node_modules" / "x.js")
    _touch(tmp_path / "web" / ".ai" / "tmp_scripts" / "a.py")
    _touch(tmp_path / "orphan" / "node_modules" / "x.js")
    _touch(tmp_path / "py" / ".venv" / "pyvenv.cfg")
    _touch(tmp_path / "py" / ".venv" / "lib" / "__pycache__" / "x.pyc")
    _touch(tmp_path / "py" / "fake" / ".venv" / "readme.txt")
    _touch(tmp_path / "py" / "src" / "__pycache__" / "y.pyc")
    _touch(tmp_path / ".config" / "app" / "package.json")
    _touch(tmp_path / ".config" / "app" / "node_modules" / "x.js")
    _touch(tmp_path / "Library" / "proj" / "__pycache__" / "z.pyc")
    (tmp_path / "linked").symlink_to(tmp_path / "web", target_is_directory=True)
    found = find_project_entries(roots=(tmp_path,), cleanups=CLEANUPS)
    assert found == {
        "ai-scratch": [tmp_path / "web" / ".ai"],
        "node-modules": [tmp_path / "web" / "node_modules"],
        "python-venvs": [tmp_path / "py" / ".venv"],
        "python-tool-caches": [tmp_path / "py" / "src" / "__pycache__"],
    }
