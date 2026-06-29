from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import pyproject_utils_app
from stackops.scripts.python.helpers.helpers_utils import upgrade_packages


def test_upgrade_packages_captures_manifest_before_destructive_actions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
    calls: list[str] = []

    def fake_generate_uv_add_commands(pyproject_path: Path, output_path: Path) -> None:
        assert pyproject_path == project_root / "pyproject.toml"
        assert output_path == project_root / "pyproject_init.sh"
        calls.append("generate")

    def fake_clean_dependency_groups(project_root: Path, group_names: list[str], clean_all_groups: bool) -> None:
        assert project_root == tmp_path / "project"
        assert group_names == []
        assert clean_all_groups is True
        calls.append("clean")

    def fake_delete_project_venv(project_root: Path) -> None:
        assert project_root == tmp_path / "project"
        calls.append("delete")

    monkeypatch.setattr(upgrade_packages, "generate_uv_add_commands", fake_generate_uv_add_commands)
    monkeypatch.setattr(upgrade_packages, "clean_dependency_groups", fake_clean_dependency_groups)
    monkeypatch.setattr(upgrade_packages, "delete_project_venv", fake_delete_project_venv)

    result = CliRunner().invoke(pyproject_utils_app.get_app(), ["upgrade-packages", str(project_root), "--clean-all-groups", "--delete-venv"])

    assert result.exit_code == 0
    assert calls == ["generate", "clean", "delete"]


def test_generate_uv_add_commands_is_safe_and_complete(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    output_path = tmp_path / "pyproject_init.sh"
    pyproject_path.write_text(
        """
[project]
name = "example"
dependencies = ["requests>=2"]

[project.optional-dependencies]
plot = ["plotly[kaleido]>=6"]

[dependency-groups]
dev = ["pytest>=9"]
data = ["polars>=1"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    upgrade_packages.generate_uv_add_commands(pyproject_path=pyproject_path, output_path=output_path)

    assert (
        output_path.read_text(encoding="utf-8")
        == """#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
uv add --frozen requests
uv add --frozen --optional plot 'plotly[kaleido]'
uv add --frozen --dev pytest
uv add --frozen --group data polars
uv sync --upgrade --no-cache
"""
    )
    assert output_path.stat().st_mode & 0o777 == 0o755


def test_clean_dependency_groups_rolls_back_partial_uv_changes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    original_pyproject = (
        """
[project]
name = "example"

[project.optional-dependencies]
plot = ["plotly>=6"]

[dependency-groups]
dev = ["python-lsp-server[mypy]>=1"]
""".strip()
        + "\n"
    )
    pyproject_path.write_text(original_pyproject, encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert check is True
        commands.append(command)
        pyproject_path.write_text("partial mutation\n", encoding="utf-8")
        if len(commands) == 2:
            raise subprocess.CalledProcessError(returncode=1, cmd=command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(upgrade_packages.subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        upgrade_packages.clean_dependency_groups(project_root=tmp_path, group_names=[], clean_all_groups=True)

    assert pyproject_path.read_text(encoding="utf-8") == original_pyproject
    assert commands == [["uv", "remove", "--optional", "plot", "plotly", "--frozen"], ["uv", "remove", "--dev", "python-lsp-server", "--frozen"]]


@pytest.mark.parametrize(
    ("dependency_spec", "expected_requirement"),
    [
        ("requests[socks]>=2; python_version < '3.14'", "requests[socks]; python_version < '3.14'"),
        ("example @ git+https://example.com/example.git@main", "example @ git+https://example.com/example.git@main"),
    ],
)
def test_build_upgrade_requirement_preserves_dependency_semantics(dependency_spec: str, expected_requirement: str) -> None:
    assert upgrade_packages.build_upgrade_requirement(dependency_spec=dependency_spec) == expected_requirement
