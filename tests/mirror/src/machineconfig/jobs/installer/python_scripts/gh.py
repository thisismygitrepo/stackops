from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import pytest

import machineconfig.jobs.installer.python_scripts.gh as gh_script
from machineconfig.utils.schemas.installer.installer_types import InstallerData


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


def test_main_linux_runs_extension_install_and_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    InstallerSpy.instances.clear()
    run_calls: list[RunCall] = []

    def fake_run(*args: object, **kwargs: object) -> int:
        run_calls.append(RunCall(args=args, kwargs=dict(kwargs)))
        return 0

    monkeypatch.setattr(gh_script, "Installer", InstallerSpy)
    monkeypatch.setattr(gh_script.platform, "system", lambda: "Linux")
    monkeypatch.setattr(gh_script.subprocess, "run", fake_run)

    gh_script.main(version="2.0.0")

    assert len(InstallerSpy.instances) == 1
    assert InstallerSpy.instances[0].installer_data == gh_script.config_dict
    assert InstallerSpy.instances[0].installed_versions == ["2.0.0"]
    assert len(run_calls) == 1
    program = run_calls[0].args[0]
    assert isinstance(program, str)
    assert "gh extension install github/gh-copilot" in program
    assert "gh auth login --with-token $HOME/dotfiles/creds/git/gh_token.txt" in program
    assert run_calls[0].kwargs == {"shell": True, "text": True, "check": True}


def test_main_rejects_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    InstallerSpy.instances.clear()
    monkeypatch.setattr(gh_script, "Installer", InstallerSpy)
    monkeypatch.setattr(gh_script.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        gh_script.main(version=None)

    assert len(InstallerSpy.instances) == 1
    assert InstallerSpy.instances[0].installed_versions == [None]
