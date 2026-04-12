from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

import pytest

import machineconfig.jobs.installer.python_scripts.espanso as espanso_script
from machineconfig.utils.schemas.installer.installer_types import InstallerData


BASE_INSTALLER_DATA = cast(
    InstallerData,
    {
        "appName": "espanso",
        "license": "GPL",
        "doc": "expander",
    },
)


@dataclass(frozen=True)
class RunCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]


class InstallerSpy:
    instances: ClassVar[list["InstallerSpy"]] = []

    def __init__(self, installer_data: InstallerData) -> None:
        self.installer_data = installer_data
        self.installed_versions: list[str | None] = []
        type(self).instances.append(self)

    def install(self, version: str | None) -> None:
        self.installed_versions.append(version)


def test_build_installer_data_for_linux_wayland() -> None:
    resolved = espanso_script._build_espanso_installer_data(
        base_installer_data=BASE_INSTALLER_DATA,
        os_name="linux",
        arch="amd64",
        xdg_session_type="wayland",
    )

    assert resolved["repoURL"] == espanso_script.ESPANSO_REPO_URL
    assert resolved["fileNamePattern"]["amd64"]["linux"] == "espanso-debian-wayland-amd64.deb"
    assert resolved["fileNamePattern"]["amd64"]["windows"] is None


def test_build_installer_data_requires_xdg_session_type_on_linux() -> None:
    with pytest.raises(
        RuntimeError,
        match="XDG_SESSION_TYPE must be set for Linux Espanso installations",
    ):
        espanso_script._build_espanso_installer_data(
            base_installer_data=BASE_INSTALLER_DATA,
            os_name="linux",
            arch="amd64",
            xdg_session_type=None,
        )


def test_main_linux_wayland_runs_installer_and_postinstall_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    InstallerSpy.instances.clear()
    run_calls: list[RunCall] = []

    def fake_run(*args: object, **kwargs: object) -> int:
        run_calls.append(RunCall(args=args, kwargs=dict(kwargs)))
        return 0

    monkeypatch.setattr(espanso_script, "Installer", InstallerSpy)
    monkeypatch.setattr(espanso_script, "get_os_name", lambda: "linux")
    monkeypatch.setattr(espanso_script, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(espanso_script.subprocess, "run", fake_run)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")

    espanso_script.main(
        installer_data=BASE_INSTALLER_DATA,
        version="1.0.0",
        update=False,
    )

    assert len(InstallerSpy.instances) == 1
    assert InstallerSpy.instances[0].installer_data["fileNamePattern"]["amd64"]["linux"] == "espanso-debian-wayland-amd64.deb"
    assert InstallerSpy.instances[0].installed_versions == ["1.0.0"]
    assert len(run_calls) == 1
    assert "espanso service register" in cast(str, run_calls[0].args[0])
    assert run_calls[0].kwargs == {"shell": True, "text": True, "check": True}
