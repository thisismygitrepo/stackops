from typing import cast

import pytest
import typer

from stackops.scripts.python.helpers.helpers_utils import machine_utils_app
from stackops.utils import procs


def test_kill_process_rejects_invalid_filter_before_initializing_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    initialized: list[bool] = []

    class FakeProcessManager:
        def __init__(self) -> None:
            initialized.append(True)

    monkeypatch.setattr(procs, "ProcessManager", FakeProcessManager)

    with pytest.raises(typer.Exit) as exc_info:
        machine_utils_app.kill_process(cast(machine_utils_app.ProcessSearchField, "bogus"))

    assert exc_info.value.exit_code == 1
    assert initialized == []
