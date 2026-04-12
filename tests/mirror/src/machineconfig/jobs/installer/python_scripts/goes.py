from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import machineconfig.jobs.installer.python_scripts.goes as goes_script
from machineconfig.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {})


@dataclass(frozen=True)
class RunCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]


def test_main_runs_expected_install_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_calls: list[RunCall] = []

    def fake_run(*args: object, **kwargs: object) -> int:
        run_calls.append(RunCall(args=args, kwargs=dict(kwargs)))
        return 0

    monkeypatch.setattr(goes_script.subprocess, "run", fake_run)

    goes_script.main(installer_data=DUMMY_INSTALLER_DATA)

    assert len(run_calls) == 1
    script = run_calls[0].args[0]
    assert isinstance(script, str)
    assert "git clone https://github.com/ShishirPatil/gorilla --depth 1" in script
    assert "uv sync" in script
    assert run_calls[0].kwargs == {"shell": True, "text": True, "check": True}
