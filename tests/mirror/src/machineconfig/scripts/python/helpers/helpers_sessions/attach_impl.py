from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType
from typing import Literal, cast

import pytest

import machineconfig.scripts.python.helpers.helpers_sessions.attach_impl as subject


def test_strip_ansi_codes_and_natural_sort_key() -> None:
    raw = "\x1b[31mTab10\x1b[0m next"

    assert subject.strip_ansi_codes(raw) == "Tab10 next"
    assert sorted(["tab10", "tab2", "Tab1"], key=subject.natural_sort_key) == ["Tab1", "tab2", "tab10"]


def test_run_command_captures_process_result() -> None:
    result = subject.run_command([sys.executable, "-c", "import sys; print('ok'); sys.stderr.write('warn\\n'); raise SystemExit(3)"])

    assert result.returncode == 3
    assert result.stdout == "ok\n"
    assert result.stderr == "warn\n"


def test_interactive_choose_with_preview_uses_tv_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    module = ModuleType("machineconfig.utils.options_utils.tv_options")

    def choose_from_dict_with_preview(
        *, options_to_preview_mapping: dict[str, str], extension: str, multi: bool, preview_size_percent: float
    ) -> list[str] | str:
        captured["mapping"] = options_to_preview_mapping
        captured["extension"] = extension
        captured["multi"] = multi
        captured["preview_size_percent"] = preview_size_percent
        return ["beta", "alpha"] if multi else "beta"

    setattr(module, "choose_from_dict_with_preview", choose_from_dict_with_preview)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(subject, "check_tool_exists", lambda tool: tool == "tv")

    def fail_choose_from_options(**_: object) -> list[str] | str | None:
        raise AssertionError("fallback selector should not run")

    monkeypatch.setattr(subject, "choose_from_options", fail_choose_from_options)

    chosen = subject.interactive_choose_with_preview(msg="pick", options_to_preview_mapping={"alpha": "A", "beta": "B"}, multi=True)

    assert chosen == ["beta", "alpha"]
    assert captured == {"mapping": {"alpha": "A", "beta": "B"}, "extension": "md", "multi": True, "preview_size_percent": 70.0}


def test_interactive_choose_with_preview_falls_back_when_preview_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleType("machineconfig.utils.options_utils.tv_options")

    def choose_from_dict_with_preview(
        *, options_to_preview_mapping: dict[str, str], extension: str, multi: bool, preview_size_percent: float
    ) -> list[str] | str:
        _ = options_to_preview_mapping, extension, multi, preview_size_percent
        raise RuntimeError("preview unavailable")

    setattr(module, "choose_from_dict_with_preview", choose_from_dict_with_preview)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(subject, "check_tool_exists", lambda tool: tool == "tv")

    captured: dict[str, object] = {}

    def fake_choose_from_options(**kwargs: object) -> list[str] | str | None:
        captured.update(kwargs)
        return None

    monkeypatch.setattr(subject, "choose_from_options", fake_choose_from_options)

    chosen = subject.interactive_choose_with_preview(msg="pick", options_to_preview_mapping={"alpha": "A"}, multi=True)

    assert chosen == []
    assert captured == {"msg": "pick", "multi": True, "options": ["alpha"], "tv": True, "custom_input": False}


def test_choose_session_dispatches_to_requested_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    zellij_module = ModuleType("machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend")
    tmux_module = ModuleType("machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend")

    def choose_zellij(*, name: str | None, new_session: bool, kill_all: bool, window: bool) -> tuple[str, str | None]:
        assert new_session is True
        assert kill_all is False
        assert window is True
        return ("zellij", name)

    def choose_tmux(*, name: str | None, new_session: bool, kill_all: bool, window: bool) -> tuple[str, str | None]:
        assert new_session is False
        assert kill_all is True
        assert window is False
        return ("tmux", name)

    def get_session_tabs() -> list[tuple[str, str]]:
        return [("demo", "tab-1")]

    setattr(zellij_module, "choose_session", choose_zellij)
    setattr(zellij_module, "get_session_tabs", get_session_tabs)
    setattr(tmux_module, "choose_session", choose_tmux)
    monkeypatch.setitem(sys.modules, zellij_module.__name__, zellij_module)
    monkeypatch.setitem(sys.modules, tmux_module.__name__, tmux_module)

    assert subject.choose_session("zellij", "alpha", True, False, window=True) == ("zellij", "alpha")
    assert subject.choose_session("tmux", "beta", False, True, window=False) == ("tmux", "beta")
    assert subject.get_session_tabs() == [("demo", "tab-1")]


def test_choose_session_rejects_unknown_backend() -> None:
    bad_backend = cast(Literal["zellij", "tmux"], "bad")

    with pytest.raises(ValueError, match="Unsupported backend: bad"):
        subject.choose_session(bad_backend, None, False, False)


def test_quote_handles_strings_and_paths() -> None:
    assert subject.quote("two words") == "'two words'"
    assert subject.quote(Path("/tmp/demo file")) == "'/tmp/demo file'"
