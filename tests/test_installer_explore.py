from typer.testing import CliRunner

from stackops.scripts.python.devops import get_app
from stackops.utils.installer_utils.installer_explore import (
    _build_category_label_options,
    _group_installers_by_category_label,
)
from stackops.utils.schemas.installer.installer_types import InstallerCategoryLabel, InstallerData


def _installer_data(app_name: str, category_labels: list[InstallerCategoryLabel]) -> InstallerData:
    return {
        "appName": app_name,
        "license": "MIT",
        "repoURL": "https://github.com/example/example",
        "doc": f"{app_name} docs",
        "categoryLabels": category_labels,
        "fileNamePattern": {
            "amd64": {"linux": "example", "windows": "example.exe", "darwin": "example"},
            "arm64": {"linux": "example", "windows": "example.exe", "darwin": "example"},
        },
    }


def test_install_help_exposes_explore_option() -> None:
    result = CliRunner().invoke(get_app(), ["install", "--help"])

    assert result.exit_code == 0
    assert "--explore" in result.output
    assert "-x" in result.output


def test_category_label_options_group_installers_by_label() -> None:
    installers = [
        _installer_data("duckdb", ["databases"]),
        _installer_data("rainfrog", ["databases"]),
        _installer_data("lazygit", ["version-control"]),
    ]

    grouped = _group_installers_by_category_label(installers)
    options = _build_category_label_options(
        category_to_installers=grouped,
        category_definitions={
            "databases": {"label": "Databases & SQL Clients", "description": ""},
            "version-control": {"label": "Version Control", "description": ""},
        },
    )

    assert grouped["databases"] == installers[:2]
    assert any("databases" in option and "2 apps" in option for option in options)
    assert any("version-control" in option and "1 apps" in option for option in options)
