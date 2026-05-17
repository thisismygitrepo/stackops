import pytest

from stackops.utils.upgrade_packages import CleanupTarget, PyprojectTable, resolve_cleanup_targets


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
