from __future__ import annotations

import sys
from types import ModuleType
from typing import Literal, cast

import pytest

import machineconfig.scripts.python.helpers.helpers_sessions.kill_impl as subject


@pytest.mark.parametrize(
    ("backend", "module_name"),
    [
        ("zellij", "machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend"),
        ("tmux", "machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend"),
    ],
)
def test_choose_kill_target_dispatches(backend: Literal["zellij", "tmux"], module_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleType(module_name)

    def choose_kill_target(*, name: str | None, kill_all: bool, window: bool) -> tuple[str, str | None]:
        assert kill_all is True
        assert window is False
        return (backend, name)

    setattr(module, "choose_kill_target", choose_kill_target)
    monkeypatch.setitem(sys.modules, module_name, module)

    assert subject.choose_kill_target(backend, "demo", kill_all=True, window=False) == (backend, "demo")


def test_choose_kill_target_rejects_unknown_backend() -> None:
    bad_backend = cast(Literal["zellij", "tmux"], "bad")

    with pytest.raises(ValueError, match="Unsupported backend: bad"):
        subject.choose_kill_target(bad_backend, None)
