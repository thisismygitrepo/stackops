from pathlib import Path

import pytest

from stackops.scripts.python.enums import BACKENDS_MAP
from stackops.scripts.python.helpers.helpers_preview import preview_impl


def test_jupyter_ai_alias_resolves_to_backend() -> None:
    assert BACKENDS_MAP["ja"] == "jupyter-ai"


def test_build_read_command_adds_jupyter_ai_requirement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preview_impl, "STACKOPS_REPO_DIR", tmp_path)
    nb_target = tmp_path / "preview.ipynb"

    command = preview_impl.build_read_command(
        file_obj=tmp_path / "data.py",
        pyfile=tmp_path / "script.py",
        nb_target=nb_target,
        backend="jupyter-ai",
        ipython_profile="default",
        uv_python_line="--python 3.14",
        uv_project_line='--project "."',
        user_uv_with_line="",
        uv_with=None,
    )

    assert "--with jupyterlab" in command
    assert "--with jupyter-ai" in command
    assert f"jupyter-lab {nb_target}" in command


def test_build_read_command_installs_jupyterlab_without_stackops_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preview_impl, "STACKOPS_REPO_DIR", tmp_path / "missing")
    nb_target = tmp_path / "preview.ipynb"

    command = preview_impl.build_read_command(
        file_obj=tmp_path / "data.py",
        pyfile=tmp_path / "script.py",
        nb_target=nb_target,
        backend="jupyter",
        ipython_profile="default",
        uv_python_line="--python 3.14",
        uv_project_line="",
        user_uv_with_line="",
        uv_with=None,
    )

    assert "--with jupyterlab" in command
    assert f"jupyter-lab {nb_target}" in command
