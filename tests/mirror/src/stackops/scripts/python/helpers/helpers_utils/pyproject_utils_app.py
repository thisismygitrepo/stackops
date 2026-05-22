from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import pyproject_utils_app


def test_upgrade_packages_supports_clean_all_groups_and_delete_venv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_clean_dependency_groups(
        project_root: Path,
        group_names: list[str],
        clean_all_groups: bool,
    ) -> None:
        calls["clean_project_root"] = project_root
        calls["clean_group_names"] = group_names
        calls["clean_all_groups"] = clean_all_groups

    def fake_delete_project_venv(project_root: Path) -> None:
        calls["delete_project_root"] = project_root

    def fake_generate_uv_add_commands(pyproject_path: Path, output_path: Path) -> None:
        calls["pyproject_path"] = pyproject_path
        calls["output_path"] = output_path

    monkeypatch.setattr(
        "stackops.utils.upgrade_packages.clean_dependency_groups",
        fake_clean_dependency_groups,
    )
    monkeypatch.setattr(
        "stackops.utils.upgrade_packages.delete_project_venv",
        fake_delete_project_venv,
    )
    monkeypatch.setattr(
        "stackops.utils.upgrade_packages.generate_uv_add_commands",
        fake_generate_uv_add_commands,
    )

    result = CliRunner().invoke(
        pyproject_utils_app.get_app(),
        ["upgrade-packages", str(repo_root), "--clean-all-groups", "--delete-venv"],
    )

    assert result.exit_code == 0
    assert calls == {
        "clean_project_root": repo_root.resolve(),
        "clean_group_names": [],
        "clean_all_groups": True,
        "delete_project_root": repo_root.resolve(),
        "pyproject_path": repo_root.resolve().joinpath("pyproject.toml"),
        "output_path": repo_root.resolve().joinpath("pyproject_init.sh"),
    }
