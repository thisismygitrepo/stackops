from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from textual.widgets import ListView

from machineconfig.scripts.python.helpers.helper_env import path_manager_tui


class UpdateRecorder:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def __call__(self, renderable: object) -> None:
        self.messages.append(renderable)


class FakeLabel:
    def __init__(self, text: str) -> None:
        self._text = text

    def render(self) -> str:
        return self._text


class FakeListItem:
    def __init__(self, label: FakeLabel) -> None:
        self.label = label
        self.set_class_calls: list[tuple[bool, str]] = []

    def set_class(self, enabled: bool, class_name: str) -> None:
        self.set_class_calls.append((enabled, class_name))

    def query_one(self, label_type: type[FakeLabel]) -> FakeLabel:
        _ = label_type
        return self.label


class FakeListView:
    def __init__(self) -> None:
        self.items: list[FakeListItem] = []
        self.cleared = False

    def clear(self) -> None:
        self.cleared = True
        self.items.clear()

    def append(self, item: FakeListItem) -> None:
        self.items.append(item)


class FakePreview:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def update_preview(self, directory: str) -> None:
        self.paths.append(directory)


class FakeStatus:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def show_message(self, message: str, message_type: str) -> None:
        self.messages.append((message, message_type))


class QueryRouter:
    def __init__(self, list_view: FakeListView, preview: FakePreview, status: FakeStatus) -> None:
        self._list_view = list_view
        self._preview = preview
        self._status = status

    def __call__(self, selector: str, expected_type: type[object]) -> object:
        _ = expected_type
        if selector == "#path-list":
            return self._list_view
        if selector == "#preview":
            return self._preview
        if selector == "#status":
            return self._status
        raise AssertionError(f"Unexpected selector: {selector}")


class FakeApp:
    def __init__(self) -> None:
        self.run_calls = 0

    def run(self) -> None:
        self.run_calls += 1


def test_directory_preview_accepts_widget_id(monkeypatch: pytest.MonkeyPatch) -> None:
    preview = path_manager_tui.DirectoryPreview(widget_id="preview")
    recorder = UpdateRecorder()

    monkeypatch.setattr(preview, "update", recorder)
    preview.update_preview("")

    assert preview.id == "preview"
    assert recorder.messages == ["Select a PATH entry to preview its contents"]


def test_status_bar_wraps_warning_in_yellow(monkeypatch: pytest.MonkeyPatch) -> None:
    status = path_manager_tui.StatusBar(widget_id="status")
    recorder = UpdateRecorder()

    monkeypatch.setattr(status, "update", recorder)
    status.show_message("Missing PATH entry", "warning")

    assert status.id == "status"
    assert recorder.messages == ["[yellow]Missing PATH entry[/yellow]"]


def test_refresh_path_list_marks_existing_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    existing_path = tmp_path.joinpath("bin")
    existing_path.mkdir()
    missing_path = tmp_path.joinpath("missing")
    app = path_manager_tui.PathExplorerApp()
    list_view = FakeListView()
    preview = FakePreview()
    status = FakeStatus()
    router = QueryRouter(list_view, preview, status)

    def fake_get_path_entries() -> list[str]:
        return [existing_path.as_posix(), missing_path.as_posix()]

    monkeypatch.setattr(path_manager_tui, "get_path_entries", fake_get_path_entries)
    monkeypatch.setattr(path_manager_tui, "Label", FakeLabel)
    monkeypatch.setattr(path_manager_tui, "ListItem", FakeListItem)
    monkeypatch.setattr(app, "query_one", router)

    app.refresh_path_list()

    assert [item.label.render() for item in list_view.items] == [f"✅ {existing_path.as_posix()}", f"❌ {missing_path.as_posix()}"]
    assert status.messages == [("Loaded 2 PATH entries", "success")]


def test_handle_highlight_updates_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    app = path_manager_tui.PathExplorerApp()
    list_view = FakeListView()
    preview = FakePreview()
    status = FakeStatus()
    router = QueryRouter(list_view, preview, status)
    item = FakeListItem(FakeLabel("✅ /opt/tools"))
    event = cast(ListView.Highlighted, SimpleNamespace(item=item))

    monkeypatch.setattr(app, "query_one", router)

    app.handle_highlight(event)

    assert preview.paths == ["/opt/tools"]
    assert status.messages == [("Previewing: /opt/tools", "info")]


def test_action_copy_path_warns_without_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    app = path_manager_tui.PathExplorerApp()
    list_view = FakeListView()
    preview = FakePreview()
    status = FakeStatus()
    router = QueryRouter(list_view, preview, status)

    monkeypatch.setattr(app, "query_one", router)

    app.action_copy_path()

    assert status.messages == [("No PATH entry selected", "warning")]


def test_main_runs_app(monkeypatch: pytest.MonkeyPatch) -> None:
    app = FakeApp()

    def fake_path_explorer_app() -> FakeApp:
        return app

    monkeypatch.setattr(path_manager_tui, "PathExplorerApp", fake_path_explorer_app)

    path_manager_tui.main()

    assert app.run_calls == 1
