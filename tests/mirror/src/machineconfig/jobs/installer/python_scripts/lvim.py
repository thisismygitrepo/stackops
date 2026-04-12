from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

import machineconfig.jobs.installer.python_scripts.lvim as lvim_script
from machineconfig.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {})


@dataclass(frozen=True)
class RunCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]


def test_main_linux_runs_lunarvim_installer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_calls: list[RunCall] = []

    def fake_run(*args: object, **kwargs: object) -> int:
        run_calls.append(RunCall(args=args, kwargs=dict(kwargs)))
        return 0

    monkeypatch.setattr(lvim_script.platform, "system", lambda: "Linux")
    monkeypatch.setattr(lvim_script.subprocess, "run", fake_run)

    lvim_script.main(
        installer_data=DUMMY_INSTALLER_DATA,
        version="1.4.0",
        update=False,
    )

    assert len(run_calls) == 1
    program = run_calls[0].args[0]
    assert isinstance(program, str)
    assert "release-1.4/neovim-0.9" in program
    assert "install.sh" in program
    assert run_calls[0].kwargs == {"shell": True, "check": True}


def test_main_rejects_unsupported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lvim_script.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        lvim_script.main(
            installer_data=DUMMY_INSTALLER_DATA,
            version=None,
            update=False,
        )
