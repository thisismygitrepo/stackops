from pathlib import Path
from unittest.mock import Mock, call

import pytest

import stackops.jobs.installer.python_scripts.deer_flow as deer_flow
from stackops.utils.schemas.installer.installer_types import InstallerData


DEER_FLOW_INSTALLER_DATA: InstallerData = {
    "appName": "deer-flow",
    "license": "MIT License",
    "repoURL": deer_flow.DEER_FLOW_REPOSITORY_URL,
    "doc": "DeerFlow",
    "categoryLabels": ["ai-agents-assistants"],
    "fileNamePattern": {
        "amd64": {"linux": "deer_flow.py", "windows": "deer_flow.py", "darwin": "deer_flow.py"},
        "arm64": {"linux": "deer_flow.py", "windows": "deer_flow.py", "darwin": "deer_flow.py"},
    },
}


def test_main_clones_and_configures_new_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_root = tmp_path.joinpath("deer-flow")
    run_mock = Mock()
    monkeypatch.setattr(deer_flow, "DEER_FLOW_INSTALL_ROOT", install_root)
    monkeypatch.setattr(deer_flow.platform, "system", Mock(return_value="Darwin"))
    monkeypatch.setattr(deer_flow.subprocess, "run", run_mock)

    deer_flow.main(installer_data=DEER_FLOW_INSTALLER_DATA, version=None, update=False)

    assert install_root.parent.is_dir()
    assert run_mock.call_args_list == [
        call(
            ["git", "clone", deer_flow.DEER_FLOW_REPOSITORY_URL, str(install_root)],
            check=True,
        ),
        call(["make", "setup"], cwd=install_root, check=True),
    ]


def test_main_updates_configured_workspace_without_replacing_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_root = tmp_path.joinpath("deer-flow")
    install_root.joinpath(".git").mkdir(parents=True)
    config_path = install_root.joinpath("config.yaml")
    config_path.write_text("models: []\n", encoding="utf-8")
    run_mock = Mock()
    monkeypatch.setattr(deer_flow, "DEER_FLOW_INSTALL_ROOT", install_root)
    monkeypatch.setattr(deer_flow.subprocess, "run", run_mock)

    deer_flow.main(installer_data=DEER_FLOW_INSTALLER_DATA, version=None, update=True)

    assert config_path.read_text(encoding="utf-8") == "models: []\n"
    run_mock.assert_called_once_with(
        ["git", "-C", str(install_root), "pull", "--ff-only"],
        check=True,
    )
