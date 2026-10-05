from unittest.mock import Mock, call

import pytest

from stackops.scripts.python.helpers.helpers_devops import devops_status_apps
from stackops.utils.schemas.installer.installer_types import InstallerData, InstallerCategoryLabel


@pytest.mark.parametrize(
    ("app_name", "executable_name"),
    [("superfile", "spf"), ("agent-git", "agit"), ("antigravity", "agy"), ("beads", "bd"), ("orca", "orca-ide")],
)
def test_apps_status_uses_installer_executables_and_catalog_categories(
    monkeypatch: pytest.MonkeyPatch,
    app_name: str,
    executable_name: str,
) -> None:
    categories: list[InstallerCategoryLabel] = ["ai-agents-assistants", "productivity-knowledge"]
    installer_data: InstallerData = {
        "appName": app_name,
        "license": "MIT",
        "repoURL": "https://example.test/app",
        "doc": "Example app",
        "categoryLabels": categories,
        "fileNamePattern": {
            "amd64": {"windows": None, "linux": "example", "darwin": None},
            "arm64": {"windows": None, "linux": None, "darwin": None},
        },
    }
    catalog = Mock(return_value=[installer_data])
    detection = Mock(return_value=True)
    monkeypatch.setattr(devops_status_apps, "get_installers_from_source", catalog)
    monkeypatch.setattr(devops_status_apps, "get_os_name", Mock(return_value="linux"))
    monkeypatch.setattr(devops_status_apps, "get_normalized_arch", Mock(return_value="amd64"))
    monkeypatch.setattr("stackops.utils.installer_utils.installer_class.platform.system", Mock(return_value="Linux"))
    monkeypatch.setattr(devops_status_apps, "check_tool_exists", detection)

    grouped_status = devops_status_apps.check_important_tools()

    catalog.assert_called_once_with(source="all", os="linux", arch="amd64", which_cats=None)
    assert detection.call_args_list == [call(tool_name=executable_name)]
    assert grouped_status == {category: {app_name: True} for category in categories}


def test_apps_status_keeps_missing_installer_apps_in_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    installer_data: InstallerData = {
        "appName": "example-app",
        "license": "MIT",
        "repoURL": "https://example.test/app",
        "doc": "Example app",
        "categoryLabels": ["productivity-knowledge"],
        "fileNamePattern": {
            "amd64": {"windows": None, "linux": "example", "darwin": None},
            "arm64": {"windows": None, "linux": None, "darwin": None},
        },
    }
    monkeypatch.setattr(devops_status_apps, "get_installers_from_source", Mock(return_value=[installer_data]))
    monkeypatch.setattr(devops_status_apps, "get_os_name", Mock(return_value="linux"))
    monkeypatch.setattr(devops_status_apps, "get_normalized_arch", Mock(return_value="amd64"))
    monkeypatch.setattr(devops_status_apps, "check_tool_exists", Mock(return_value=False))

    assert devops_status_apps.check_important_tools() == {"productivity-knowledge": {"example-app": False}}
