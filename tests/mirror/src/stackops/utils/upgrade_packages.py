from pathlib import Path

import pytest

from stackops.utils.upgrade_packages import (
    CleanupTarget,
    PyprojectTable,
    delete_project_venv,
    list_all_cleanup_target_selectors,
    resolve_cleanup_targets,
)


def test_resolve_cleanup_targets_rejects_ambiguous_group_name() -> None:
    pyproject_data: PyprojectTable = {
        "project": {"optional-dependencies": {"plot": ["plotly>=1.0"]}},
        "dependency-groups": {"plot": ["matplotlib>=1.0"]},
    }

    with pytest.raises(ValueError, match="ambiguous"):
        resolve_cleanup_targets(pyproject_data=pyproject_data, group_names=["plot"])


def test_resolve_cleanup_targets_accepts_optional_dependency_selector() -> None:
    pyproject_data: PyprojectTable = {
        "project": {"optional-dependencies": {"plot": ["plotly>=1.0"]}},
        "dependency-groups": {"plot": ["matplotlib>=1.0"]},
    }

    cleanup_targets = resolve_cleanup_targets(pyproject_data=pyproject_data, group_names=["optional-dependency:plot"])

    assert cleanup_targets == [CleanupTarget(kind="optional-dependency", group_name="plot", packages=("plotly",))]


def test_resolve_cleanup_targets_accepts_dependency_group_selector() -> None:
    pyproject_data: PyprojectTable = {
        "project": {"optional-dependencies": {"plot": ["plotly>=1.0"]}},
        "dependency-groups": {"plot": ["matplotlib>=1.0"]},
    }

    cleanup_targets = resolve_cleanup_targets(pyproject_data=pyproject_data, group_names=["dependency-group:plot"])

    assert cleanup_targets == [CleanupTarget(kind="dependency-group", group_name="plot", packages=("matplotlib",))]


def test_list_all_cleanup_target_selectors_qualifies_every_group() -> None:
    pyproject_data: PyprojectTable = {
        "project": {"optional-dependencies": {"plot": ["plotly>=1.0"], "docs": []}},
        "dependency-groups": {"plot": ["matplotlib>=1.0"], "dev": ["pytest>=1.0"]},
    }

    cleanup_target_selectors = list_all_cleanup_target_selectors(pyproject_data=pyproject_data)

    assert cleanup_target_selectors == (
        "optional-dependency:plot",
        "optional-dependency:docs",
        "dependency-group:plot",
        "dependency-group:dev",
    )


def test_delete_project_venv_deletes_directory(tmp_path: Path) -> None:
    venv_path = tmp_path.joinpath(".venv")
    venv_path.mkdir()
    venv_path.joinpath("pyvenv.cfg").write_text("home = /tmp/python\n", encoding="utf-8")

    delete_project_venv(project_root=tmp_path)

    assert venv_path.exists() is False


def test_delete_project_venv_rejects_non_directory(tmp_path: Path) -> None:
    venv_path = tmp_path.joinpath(".venv")
    venv_path.write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match="directory or symlink"):
        delete_project_venv(project_root=tmp_path)
