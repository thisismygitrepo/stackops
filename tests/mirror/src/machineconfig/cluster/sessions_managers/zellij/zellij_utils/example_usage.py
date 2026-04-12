from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, NoReturn

import pytest

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import example_usage as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


@dataclass(slots=True)
class FakeLayoutGenerator:
    calls: list[LayoutConfig] = field(default_factory=list)

    def generate_layout_content(self, layout_config: LayoutConfig) -> str:
        self.calls.append(layout_config)
        return "layout-content"


@dataclass(slots=True)
class FakeProcessMonitor:
    calls: list[LayoutConfig] = field(default_factory=list)

    def check_all_commands_status(self, layout_config: LayoutConfig) -> dict[str, object]:
        self.calls.append(layout_config)
        return {"bot": {"running": True}}


@dataclass(slots=True)
class FakeStatusReporter:
    calls: list[LayoutConfig] = field(default_factory=list)

    def print_status_report(self, layout_config: LayoutConfig) -> None:
        self.calls.append(layout_config)


@dataclass(slots=True)
class FakeRemoteExecutor:
    remote_name: str


class FakeGenerator:
    instances: ClassVar[list["FakeGenerator"]] = []

    def __init__(self, remote_name: str, session_name: str, layout_config: LayoutConfig) -> None:
        self.remote_name = remote_name
        self.session_name = session_name
        self.layout_config = layout_config
        self.layout_created = False
        self.layout_generator = FakeLayoutGenerator()
        self.process_monitor = FakeProcessMonitor()
        self.status_reporter = FakeStatusReporter()
        self.remote_executor = FakeRemoteExecutor(remote_name=remote_name)
        self.__class__.instances.append(self)

    def create_layout_file(self) -> bool:
        self.layout_created = True
        return True


def _raise_runtime_error(*_args: object, **_kwargs: object) -> NoReturn:
    raise RuntimeError("boom")


def test_example_usage_runs_all_components(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    FakeGenerator.instances.clear()
    monkeypatch.setattr(subject, "ZellijRemoteLayoutGenerator", FakeGenerator)

    subject.example_usage()

    instance = FakeGenerator.instances[0]
    output = capsys.readouterr().out

    assert instance.layout_created is True
    assert instance.layout_generator.calls == [instance.layout_config, instance.layout_config]
    assert instance.process_monitor.calls == [instance.layout_config]
    assert instance.status_reporter.calls == [instance.layout_config]
    assert "Layout preview:\nlayout-content" in output
    assert "Remote executor: myserver" in output
    assert "Layout content length: 14 characters" in output
    assert "Command status check completed for 1 commands" in output
    assert "All modular components working correctly!" in output


def test_example_usage_reports_generator_errors(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(subject, "ZellijRemoteLayoutGenerator", _raise_runtime_error)

    subject.example_usage()

    output = capsys.readouterr().out
    assert "Error: boom" in output
