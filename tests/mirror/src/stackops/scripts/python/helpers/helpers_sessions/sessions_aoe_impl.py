from __future__ import annotations

from dataclasses import replace
import subprocess

import pytest

import stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl as subject
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


BASE_OPTIONS = subject.AoeLaunchOptions(
    aoe_bin="aoe",
    agent=None,
    model=None,
    provider=None,
    sandbox=None,
    yolo=False,
    cmd=None,
    extra_agent_args=(),
    env_vars=(),
    force=False,
    dry_run=False,
    sleep_inbetween=0.0,
    tab_command_mode="prompt",
    launch=False,
)


@pytest.mark.parametrize("raw_value", ["MISSING", "=value"])
def test_validate_env_vars_rejects_invalid_values(raw_value: str) -> None:
    with pytest.raises(ValueError, match="Invalid --env value"):
        subject._validate_env_vars((raw_value,))


def test_build_modern_aoe_add_command_includes_provider_and_override() -> None:
    tab: TabConfig = {"tabName": "main", "startDir": "/tmp/work", "command": "echo hi"}
    options = replace(
        BASE_OPTIONS,
        agent="codex",
        model="gpt-5.4",
        provider="openai",
        sandbox="workspace-write",
        yolo=True,
        extra_agent_args=("--debug",),
        tab_command_mode="cmd",
    )

    command = subject._build_modern_aoe_add_command(tab=tab, title="main", group="group-a", options=options)

    assert command[:11] == ["aoe", "add", "/tmp/work", "--title", "main", "--group", "group-a", "--cmd", "codex", "--yolo", "--cmd-override"]
    assert command[11] == "echo hi"
    assert command[12] == "--extra-args"
    assert command[13] == ("--model gpt-5.4 --config 'model_provider=\"openai\"' --sandbox workspace-write --debug")


def test_build_modern_aoe_add_command_rejects_provider_for_non_codex_agent() -> None:
    tab: TabConfig = {"tabName": "main", "startDir": "/tmp/work", "command": "echo hi"}
    options = replace(BASE_OPTIONS, agent="claude", provider="anthropic")

    with pytest.raises(ValueError, match="--provider"):
        subject._build_modern_aoe_add_command(tab=tab, title="main", group="group-a", options=options)


def test_inspect_aoe_add_interface_detects_modern(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=0, stdout="usage: aoe add --cmd-override", stderr=""),
    )

    interface = subject._inspect_aoe_add_interface("aoe")

    assert interface == subject.AoeAddInterface(style="modern")


def test_inspect_aoe_add_interface_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=2, stdout="", stderr="boom")
    )

    with pytest.raises(ValueError, match="Could not inspect AoE CLI"):
        subject._inspect_aoe_add_interface("aoe")


def test_run_layouts_via_aoe_dry_run_prints_commands_and_launches(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    seen_titles: list[tuple[str, str]] = []

    def fake_build_aoe_add_command(
        *, tab: TabConfig, title: str, group: str, options: subject.AoeLaunchOptions, interface: subject.AoeAddInterface
    ) -> list[str]:
        _ = tab, interface
        seen_titles.append((group, title))
        return [options.aoe_bin, "add", title, group]

    monkeypatch.setattr(subject, "_command_exists", lambda command: False)
    monkeypatch.setattr(subject, "build_aoe_add_command", fake_build_aoe_add_command)

    layouts_selected: list[LayoutConfig] = [
        {
            "layoutName": "grp",
            "layoutTabs": [
                {"tabName": "main", "startDir": "/tmp/a", "command": "echo a"},
                {"tabName": "main", "startDir": "/tmp/b", "command": "echo b"},
            ],
        }
    ]
    options = replace(BASE_OPTIONS, dry_run=True, launch=True)

    subject.run_layouts_via_aoe(layouts_selected=layouts_selected, options=options)

    output = capsys.readouterr().out
    assert seen_titles == [("grp", "main"), ("grp", "main_2")]
    assert "aoe add main grp" in output
    assert "aoe session start main" in output
    assert "aoe add main_2 grp" in output
    assert "aoe session start main_2" in output


def test_run_layouts_via_aoe_raises_when_add_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "_command_exists", lambda command: True)
    monkeypatch.setattr(subject, "_inspect_aoe_add_interface", lambda aoe_bin: subject.AoeAddInterface(style="legacy"))
    monkeypatch.setattr(
        subject.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=1, stdout="", stderr="nope")
    )

    layouts_selected: list[LayoutConfig] = [{"layoutName": "grp", "layoutTabs": [{"tabName": "main", "startDir": "/tmp/a", "command": "echo a"}]}]

    with pytest.raises(ValueError, match="aoe add failed for group 'grp' title 'main'"):
        subject.run_layouts_via_aoe(layouts_selected=layouts_selected, options=BASE_OPTIONS)
