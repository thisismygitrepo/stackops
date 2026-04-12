from __future__ import annotations

from types import ModuleType, SimpleNamespace
import sys
from typing import cast

import pytest
from rich.text import Text
from textual.widgets import ListView

from machineconfig.scripts.python.helpers.helper_env import env_manager_tui


class FakePreview:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def show_value(self, env_key: str, env_value: str) -> None:
        self.calls.append((env_key, env_value))


class FakeStatus:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def show_message(self, message: str, level: str) -> None:
        self.messages.append((message, level))


class UpdateRecorder:
    def __init__(self) -> None:
        self.renderables: list[object] = []

    def __call__(self, renderable: object) -> None:
        self.renderables.append(renderable)


def test_truncate_text_reports_remainder_count() -> None:
    preview, remainder = env_manager_tui.truncate_text("abcdef", 4)

    assert preview == "abcd"
    assert remainder == 2


def test_format_summary_sanitizes_control_characters() -> None:
    summary = env_manager_tui.format_summary("KEY", "line-1\nline-2\tvalue", 10)

    assert summary == "KEY = line-1\\nli... (+11 chars)"


def test_collect_environment_sorts_case_insensitively() -> None:
    pairs = env_manager_tui.collect_environment({"beta": "2", "Alpha": "1", "alpha": "3"})

    assert pairs == [("Alpha", "1"), ("alpha", "3"), ("beta", "2")]


def test_env_value_preview_shows_truncation_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    preview = env_manager_tui.EnvValuePreview()
    recorder = UpdateRecorder()

    monkeypatch.setattr(preview, "update", recorder)
    monkeypatch.setattr(env_manager_tui, "VALUE_PREVIEW_LIMIT", 4)

    preview.show_value("TOKEN", "abcdef")

    renderable = recorder.renderables[0]
    assert isinstance(renderable, Text)
    assert renderable.plain == "TOKEN\n\nabcd\n... truncated 2 characters"


def test_handle_highlight_updates_preview_and_status(monkeypatch: pytest.MonkeyPatch) -> None:
    app = env_manager_tui.EnvExplorerApp()
    preview = FakePreview()
    status = FakeStatus()
    item = env_manager_tui.EnvListItem("HOME", "HOME = /tmp")
    event = cast(ListView.Highlighted, SimpleNamespace(item=item))

    monkeypatch.setattr(app, "_preview", lambda: preview)
    monkeypatch.setattr(app, "_status", lambda: status)
    setattr(app, "_env_lookup", {"HOME": "/tmp/home"})

    app.handle_highlight(event)

    assert preview.calls == [("HOME", "/tmp/home")]
    assert status.messages == [("Previewing HOME", "info")]


def test_action_copy_entry_warns_when_selection_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    app = env_manager_tui.EnvExplorerApp()
    status = FakeStatus()

    monkeypatch.setattr(app, "_status", lambda: status)

    app.action_copy_entry()

    assert status.messages == [("No variable selected.", "warning")]


def test_action_copy_entry_copies_selected_value(monkeypatch: pytest.MonkeyPatch) -> None:
    app = env_manager_tui.EnvExplorerApp()
    status = FakeStatus()
    copied: list[str] = []
    fake_pyperclip = ModuleType("pyperclip")

    def fake_copy(payload: str) -> None:
        copied.append(payload)

    setattr(fake_pyperclip, "copy", fake_copy)
    monkeypatch.setitem(sys.modules, "pyperclip", fake_pyperclip)
    monkeypatch.setattr(app, "_status", lambda: status)
    setattr(app, "_selected_key", "HOME")
    setattr(app, "_env_lookup", {"HOME": "/tmp/home"})

    app.action_copy_entry()

    assert copied == ["HOME=/tmp/home"]
    assert status.messages == [("Copied HOME to clipboard.", "success")]
