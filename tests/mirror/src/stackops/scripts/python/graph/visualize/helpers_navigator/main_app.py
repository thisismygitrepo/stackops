from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from pytest import MonkeyPatch

from stackops.scripts.python.graph.visualize.helpers_navigator.command_builder import (
    CommandBuilderScreen,
)
from stackops.scripts.python.graph.visualize.helpers_navigator.data_models import (
    CommandInfo,
)
from stackops.scripts.python.graph.visualize.helpers_navigator.main_app import (
    CommandNavigatorApp,
)


class CommandNavigatorHarness(CommandNavigatorApp):
    def handle_builder_result_for_test(self, result: str | None) -> None:
        self._handle_builder_result(result)

    def execute_command_for_test(self, command: str) -> None:
        self._execute_command(command)

    def copy_to_clipboard_for_test(self, command: str) -> None:
        self._copy_to_clipboard(command)


@dataclass
class FakeNode:
    data: CommandInfo | None


@dataclass
class FakeTree:
    cursor_node: FakeNode | None


def test_handle_builder_result_dispatches_execute_and_copy(monkeypatch: MonkeyPatch) -> None:
    app = CommandNavigatorHarness()
    executed: list[str] = []
    copied: list[str] = []

    def record_execute(command: str) -> None:
        executed.append(command)

    def record_copy(command: str) -> None:
        copied.append(command)

    monkeypatch.setattr(app, "_execute_command", record_execute)
    monkeypatch.setattr(app, "_copy_to_clipboard", record_copy)

    app.handle_builder_result_for_test("EXECUTE:graph render")
    app.handle_builder_result_for_test("COPY:graph render --format svg")
    app.handle_builder_result_for_test(None)

    assert executed == ["graph render"]
    assert copied == ["graph render --format svg"]


def test_execute_command_reports_success_error_and_timeout(monkeypatch: MonkeyPatch) -> None:
    app = CommandNavigatorHarness()
    notices: list[tuple[str, str, int | None]] = []

    def record_notice(message: str, severity: str = "information", timeout: int | None = None) -> None:
        notices.append((message, severity, timeout))

    monkeypatch.setattr(app, "notify", record_notice)

    def run_success(
        command: str,
        *,
        shell: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert shell
        assert capture_output
        assert text
        assert timeout == 30
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="rendered output",
            stderr="",
        )

    monkeypatch.setattr(
        "stackops.scripts.python.graph.visualize.helpers_navigator.main_app.subprocess.run",
        run_success,
    )
    app.execute_command_for_test("graph render")

    def run_error(
        command: str,
        *,
        shell: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout="",
            stderr="bad flag",
        )

    monkeypatch.setattr(
        "stackops.scripts.python.graph.visualize.helpers_navigator.main_app.subprocess.run",
        run_error,
    )
    app.execute_command_for_test("graph render")

    def run_timeout(
        command: str,
        *,
        shell: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(
        "stackops.scripts.python.graph.visualize.helpers_navigator.main_app.subprocess.run",
        run_timeout,
    )
    app.execute_command_for_test("graph render")

    assert notices[0] == ("Executing: graph render", "information", None)
    assert notices[1] == ("Success: rendered output...", "information", 5)
    assert notices[2] == ("Executing: graph render", "information", None)
    assert notices[3] == ("Error: bad flag...", "error", 10)
    assert notices[4] == ("Executing: graph render", "information", None)
    assert notices[5] == ("Command timed out after 30 seconds", "warning", None)


def test_action_run_command_and_build_command_handle_groups_and_commands(monkeypatch: MonkeyPatch) -> None:
    app = CommandNavigatorHarness()
    notices: list[tuple[str, str, int | None]] = []
    executed: list[str] = []
    pushed_screens: list[CommandBuilderScreen] = []

    def record_notice(message: str, severity: str = "information", timeout: int | None = None) -> None:
        notices.append((message, severity, timeout))

    def record_execute(command: str) -> None:
        executed.append(command)

    def record_push(screen: object, _callback: object) -> None:
        pushed_screens.append(cast(CommandBuilderScreen, screen))

    command_info = CommandInfo(
        name="render",
        description="Render graph",
        command="graph render",
        is_group=False,
    )
    group_info = CommandInfo(
        name="graph",
        description="Graph tools",
        command="graph",
        is_group=True,
    )

    state: dict[str, FakeTree] = {"tree": FakeTree(cursor_node=FakeNode(data=command_info))}

    def query_one(_selector: object, _expected_type: object | None = None) -> FakeTree:
        return state["tree"]

    monkeypatch.setattr(app, "query_one", query_one)
    monkeypatch.setattr(app, "notify", record_notice)
    monkeypatch.setattr(app, "_execute_command", record_execute)
    monkeypatch.setattr(app, "push_screen", record_push)

    app.action_run_command()
    app.action_build_command()

    state["tree"] = FakeTree(cursor_node=FakeNode(data=group_info))
    app.action_run_command()
    app.action_build_command()

    assert executed == ["graph render"]
    assert len(pushed_screens) == 1
    assert pushed_screens[0].command_info == command_info
    assert notices == [
        ("Cannot run command groups directly", "warning", None),
        ("Cannot build command for groups", "warning", None),
    ]


def test_copy_to_clipboard_warns_when_pyperclip_missing(monkeypatch: MonkeyPatch) -> None:
    app = CommandNavigatorHarness()
    notices: list[tuple[str, str, int | None]] = []

    def record_notice(message: str, severity: str = "information", timeout: int | None = None) -> None:
        notices.append((message, severity, timeout))

    original_import = __import__

    def raising_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "pyperclip":
            raise ImportError("missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(app, "notify", record_notice)
    monkeypatch.setattr("builtins.__import__", raising_import)

    app.copy_to_clipboard_for_test("graph render")

    assert notices == [("Install pyperclip to enable clipboard support", "warning", None)]
