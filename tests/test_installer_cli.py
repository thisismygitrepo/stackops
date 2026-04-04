import json
from unittest.mock import patch

import pytest

from machineconfig.utils.installer_utils import installer_cli
from machineconfig.utils.schemas.installer.installer_types import InstallRequest, InstallationResultSameVersion, InstallerData


def _make_installer_data(app_name: str, doc: str) -> InstallerData:
    return InstallerData(
        appName=app_name,
        license="MIT License",
        doc=doc,
        repoURL=f"https://github.com/example/{app_name.lower()}",
        fileNamePattern={
            "amd64": {
                "linux": f"{app_name.lower()}-linux.tar.gz",
                "darwin": None,
                "windows": None,
            },
            "arm64": {
                "linux": f"{app_name.lower()}-arm64.tar.gz",
                "darwin": None,
                "windows": None,
            },
        },
    )


def test_build_interactive_option_previews_uses_json_payloads() -> None:
    installer_data = _make_installer_data(app_name="fd", doc="Fast file finder")
    category_display_to_name = {"📦 core                --   fd|rg": "core"}
    installer_option_to_data = {"fd           ✅ Fast file finder": installer_data}

    with patch("machineconfig.jobs.installer.package_groups.PACKAGE_GROUP2NAMES", {"core": ["fd", "rg"]}):
        previews = installer_cli._build_interactive_option_previews(  # pyright: ignore[reportPrivateUsage]
            category_display_to_name=category_display_to_name,
            installer_option_to_data=installer_option_to_data,
        )

    assert json.loads(previews["fd           ✅ Fast file finder"]) == installer_data
    assert json.loads(previews["📦 core                --   fd|rg"]) == {
        "type": "package_group",
        "groupName": "core",
        "apps": ["fd", "rg"],
    }


def test_install_interactively_uses_tv_preview_and_installs_selected_app() -> None:
    installer_data = _make_installer_data(app_name="fd", doc="Fast file finder")
    category_label = "📦 core                --   fd|rg"
    captured_preview_map: dict[str, str] = {}

    class FakeInstaller:
        install_calls: list[tuple[InstallerData, InstallRequest]] = []

        def __init__(self, installer_data: InstallerData) -> None:
            self.installer_data = installer_data

        def get_description(self) -> str:
            return f"{self.installer_data['appName'].lower():<12} ✅ {self.installer_data['doc']}"

        def install_robust(self, install_request: InstallRequest) -> InstallationResultSameVersion:
            FakeInstaller.install_calls.append((self.installer_data, install_request))
            return InstallationResultSameVersion(
                kind="same_version",
                appName=self.installer_data["appName"],
                exeName=self.installer_data["appName"].lower(),
                emoji="😑",
                version="1.0.0",
            )

    def _fake_choose(
        *, options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float
    ) -> list[str]:
        captured_preview_map.update(options_to_preview_mapping)
        _ = extension, multi, preview_size_percent
        app_label = next(label for label in options_to_preview_mapping if label.startswith("fd"))
        return [category_label, app_label]

    with (
        patch("machineconfig.utils.installer_utils.installer_runner.get_installers", return_value=[installer_data]),
        patch("machineconfig.utils.installer_utils.installer_helper.get_group_name_to_repr", return_value={category_label: "core"}),
        patch("machineconfig.utils.installer_utils.installer_locator_utils.check_tool_exists", return_value=True),
        patch("machineconfig.jobs.installer.package_groups.PACKAGE_GROUP2NAMES", {"core": ["fd", "rg"]}),
        patch("machineconfig.utils.options_utils.tv_options.choose_from_dict_with_preview", side_effect=_fake_choose),
        patch("machineconfig.utils.installer_utils.installer_class.Installer", FakeInstaller),
        patch.object(installer_cli, "install_group") as install_group,
    ):
        installer_cli.install_interactively(install_request=InstallRequest(version="v1.2.3", update=True))

    assert json.loads(next(value for key, value in captured_preview_map.items() if key.startswith("fd"))) == installer_data
    install_group.assert_called_once_with(package_group="core", install_request=InstallRequest(version="v1.2.3", update=True))
    assert FakeInstaller.install_calls == [(installer_data, InstallRequest(version="v1.2.3", update=True))]


def test_install_if_missing_uses_explicit_binary_name() -> None:
    with patch("machineconfig.utils.installer_utils.installer_locator_utils.check_tool_exists", return_value=True) as check_tool_exists:
        result = installer_cli.install_if_missing(which="poppler", binary_name="pdftoppm", verbose=True)

    assert result is True
    check_tool_exists.assert_called_once_with("pdftoppm")


def test_install_if_missing_uses_which_when_binary_name_is_none(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("machineconfig.utils.installer_utils.installer_locator_utils.check_tool_exists", return_value=False) as check_tool_exists,
        patch.object(installer_cli, "main_installer_cli") as main_installer_cli,
    ):
        result = installer_cli.install_if_missing(which="fd", binary_name=None, verbose=False)

    captured = capsys.readouterr()
    assert result is True
    check_tool_exists.assert_called_once_with("fd")
    main_installer_cli.assert_called_once_with(which="fd", interactive=False, update=False, version=None)
    assert captured.out == ""
