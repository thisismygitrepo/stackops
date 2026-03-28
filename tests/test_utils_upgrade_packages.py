from pathlib import Path
from unittest.mock import call, patch

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python import utils as utils_cli
from machineconfig.utils import upgrade_packages as upgrade_packages_utils


runner = CliRunner()


def test_upgrade_packages_help_includes_clean_group_option() -> None:
    result = runner.invoke(utils_cli.get_app(), ["pyproject", "a", "--help"])

    assert result.exit_code == 0
    assert "--clean-group" in result.output


def test_utils_root_help_lists_nested_apps() -> None:
    result = runner.invoke(utils_cli.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "machine" in result.output
    assert "pyproject" in result.output
    assert "file" in result.output
    assert "kill-process" not in result.output
    assert "upgrade-packages" not in result.output
    assert "download" not in result.output


@pytest.mark.parametrize(
    ("sub_app", "expected_commands"),
    [
        ("machine", ["kill-process", "environment", "get-machine-specs", "list-devices", "mount"]),
        ("pyproject", ["init-project", "upgrade-packages", "type-hint"]),
        ("file", ["edit", "download", "pdf-merge", "pdf-compress", "read-db"]),
    ],
)
def test_utils_sub_apps_expose_expected_commands(sub_app: str, expected_commands: list[str]) -> None:
    result = runner.invoke(utils_cli.get_app(), [sub_app, "--help"])

    assert result.exit_code == 0
    for command in expected_commands:
        assert command in result.output


def test_upgrade_packages_cleans_requested_groups_before_generating_script(tmp_path: Path) -> None:
    with (
        patch.object(upgrade_packages_utils, "clean_dependency_groups") as clean_dependency_groups,
        patch.object(upgrade_packages_utils, "generate_uv_add_commands") as generate_uv_add_commands,
    ):
        result = runner.invoke(
            utils_cli.get_app(),
            ["pyproject", "a", "--clean-group", "other", "--clean-group", "plot", str(tmp_path)],
        )

    resolved_root = tmp_path.resolve()

    assert result.exit_code == 0
    clean_dependency_groups.assert_called_once_with(project_root=resolved_root, group_names=["other", "plot"])
    generate_uv_add_commands.assert_called_once_with(
        pyproject_path=resolved_root / "pyproject.toml",
        output_path=resolved_root / "pyproject_init.sh",
    )


def test_clean_dependency_groups_builds_uv_remove_commands_for_all_matching_group_kinds(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[project]
name = "tmp-project"
version = "0.1.0"

[project.optional-dependencies]
plot = [
    "rich>=14.3.3",
]

[dependency-groups]
dev = [
    "pytest>=9.0.2",
]
other = [
    "duckdb-engine>=0.17.0",
    "pycrucible>=0.4.6",
]
plot = [
    "matplotlib>=3.10.8",
]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with patch.object(upgrade_packages_utils.subprocess, "run") as subprocess_run:
        upgrade_packages_utils.clean_dependency_groups(project_root=tmp_path, group_names=["plot", "other", "dev"])

    assert subprocess_run.call_args_list == [
        call(["uv", "remove", "--optional", "plot", "rich", "--no-sync"], cwd=tmp_path, check=True),
        call(["uv", "remove", "--group", "plot", "matplotlib", "--no-sync"], cwd=tmp_path, check=True),
        call(
            ["uv", "remove", "--group", "other", "duckdb-engine", "pycrucible", "--no-sync"],
            cwd=tmp_path,
            check=True,
        ),
        call(["uv", "remove", "--dev", "pytest", "--no-sync"], cwd=tmp_path, check=True),
    ]


def test_generate_uv_add_commands_preserves_optional_dependencies(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    output_path = tmp_path / "pyproject_init.sh"
    pyproject_path.write_text(
        """
[project]
name = "tmp-project"
version = "0.1.0"
dependencies = [
    "typer>=0.24.1",
]

[project.optional-dependencies]
plot = [
    "rich>=14.3.3",
]

[dependency-groups]
other = [
    "pycrucible>=0.4.6",
]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    upgrade_packages_utils.generate_uv_add_commands(pyproject_path=pyproject_path, output_path=output_path)

    output = output_path.read_text(encoding="utf-8")

    assert "uv add --no-cache 'typer'" in output
    assert "uv add --no-cache --optional plot 'rich'" in output
    assert "uv add --no-cache --group other 'pycrucible'" in output
