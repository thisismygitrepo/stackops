from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
import pytest

from stackops.scripts.python.helpers.helpers_preview import preview_impl


def test_local_preview_runtime_uses_local_plot_extra(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preview_impl, "STACKOPS_REPO_DIR", tmp_path)

    python_options, project_options = preview_impl._build_uv_runtime_options(project_path=None, backend="ipython")

    assert python_options == "--python 3.14"
    assert f'--project "{tmp_path}"' in project_options
    assert "--extra plot" in project_options
    assert "stackops[plot]" not in project_options


def test_plot_extra_provides_duckdb_sqlalchemy_dialect() -> None:
    package_requirements = distribution("stackops").requires
    assert package_requirements is not None

    plot_requirement_names = {
        requirement.name
        for requirement_text in package_requirements
        if (requirement := Requirement(requirement_text)).marker is not None
        and requirement.marker.evaluate({"extra": "plot"})
    }

    assert {"duckdb", "duckdb-engine", "polars", "sqlalchemy"} <= plot_requirement_names
