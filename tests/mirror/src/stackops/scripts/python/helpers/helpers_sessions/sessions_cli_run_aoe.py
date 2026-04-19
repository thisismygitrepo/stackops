

from pathlib import Path
from typing import cast

import pytest
import typer

import stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run_aoe as subject
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


class StubContext:
    def get_help(self) -> str:
        return "HELP"


def _make_context() -> typer.Context:
    return cast(typer.Context, StubContext())


def test_run_aoe_cli_missing_layout_file_emits_help_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path.joinpath("missing.json")
    monkeypatch.setattr(subject, "find_layout_file", lambda *, layout_path: str(missing))

    with pytest.raises(typer.Exit) as exc_info:
        subject.run_aoe_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            choose_layouts=None,
            choose_tabs=None,
            sleep_inbetween=0.1,
            max_tabs=4,
            agent=None,
            model=None,
            provider=None,
            sandbox=None,
            yolo=False,
            cmd=None,
            args=[],
            env=[],
            force=False,
            dry_run=False,
            aoe_bin="aoe",
            tab_command_mode="prompt",
            subsitute_home=False,
            launch=False,
        )

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "HELP" in captured.out
    assert str(missing) in captured.err


def test_run_aoe_cli_filters_tabs_substitutes_home_and_builds_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    layouts_path = tmp_path.joinpath("layouts.json")
    layouts_path.write_text("{}", encoding="utf-8")
    alpha_shared: TabConfig = {"tabName": "shared", "startDir": "/a", "command": "echo a"}
    alpha_only: TabConfig = {"tabName": "alpha-only", "startDir": "/a2", "command": "echo a2"}
    beta_build: TabConfig = {"tabName": "build", "startDir": "/b", "command": "echo b"}
    gamma_shared: TabConfig = {"tabName": "shared", "startDir": "/g", "command": "echo g"}
    selected_layouts: list[LayoutConfig] = [
        {"layoutName": "alpha", "layoutTabs": [alpha_shared, alpha_only]},
        {"layoutName": "beta", "layoutTabs": [beta_build]},
    ]
    all_layouts: list[LayoutConfig] = [
        {"layoutName": "alpha", "layoutTabs": [alpha_shared, alpha_only]},
        {"layoutName": "beta", "layoutTabs": [beta_build]},
        {"layoutName": "gamma", "layoutTabs": [gamma_shared]},
    ]
    captured: dict[str, object] = {}

    monkeypatch.setattr(subject, "find_layout_file", lambda *, layout_path: str(layouts_path))

    def fake_select_layout(
        *,
        layouts_json_file: str,
        selected_layouts_names: list[str],
        select_interactively: bool,
    ) -> list[LayoutConfig]:
        assert layouts_json_file == str(layouts_path)
        if selected_layouts_names:
            assert selected_layouts_names == ["alpha", "beta"]
            assert select_interactively is False
            return selected_layouts
        return all_layouts

    def fake_substitute_home(*, tabs: list[TabConfig]) -> list[TabConfig]:
        return [
            {
                "tabName": tab["tabName"],
                "startDir": f"/resolved{tab['startDir']}",
                "command": tab["command"],
            }
            for tab in tabs
        ]

    def fake_run_layouts_via_aoe(
        *,
        layouts_selected: list[LayoutConfig],
        options: subject.AoeLaunchOptions,
    ) -> None:
        captured["layouts_selected"] = layouts_selected
        captured["options"] = options

    monkeypatch.setattr(subject, "select_layout", fake_select_layout)
    monkeypatch.setattr(subject, "substitute_home", fake_substitute_home)
    monkeypatch.setattr(subject, "run_layouts_via_aoe", fake_run_layouts_via_aoe)

    subject.run_aoe_cli(
        ctx=_make_context(),
        layouts_file="layouts.json",
        choose_layouts="alpha,beta",
        choose_tabs="shared,beta::build",
        sleep_inbetween=0.5,
        max_tabs=4,
        agent="codex",
        model="gpt-5.4",
        provider="openai",
        sandbox="workspace-write",
        yolo=True,
        cmd="/bin/bash",
        args=["--debug"],
        env=["A=1"],
        force=True,
        dry_run=True,
        aoe_bin="aoe",
        tab_command_mode="prompt",
        subsitute_home=True,
        launch=True,
    )

    options = cast(subject.AoeLaunchOptions, captured["options"])
    assert captured["layouts_selected"] == [
        {
            "layoutName": "alpha",
            "layoutTabs": [
                {"tabName": "shared", "startDir": "/resolved/a", "command": "echo a"}
            ],
        },
        {
            "layoutName": "beta",
            "layoutTabs": [
                {"tabName": "build", "startDir": "/resolved/b", "command": "echo b"}
            ],
        },
    ]
    assert options == subject.AoeLaunchOptions(
        aoe_bin="aoe",
        agent="codex",
        model="gpt-5.4",
        provider="openai",
        sandbox="workspace-write",
        yolo=True,
        cmd="/bin/bash",
        extra_agent_args=("--debug",),
        env_vars=("A=1",),
        force=True,
        dry_run=True,
        sleep_inbetween=0.5,
        tab_command_mode="prompt",
        launch=True,
    )


def test_run_aoe_cli_rejects_unknown_tab_selector(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    layouts_path = tmp_path.joinpath("layouts.json")
    layouts_path.write_text("{}", encoding="utf-8")
    layouts_selected: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "shared", "startDir": "/a", "command": "echo a"}],
        }
    ]

    monkeypatch.setattr(subject, "find_layout_file", lambda *, layout_path: str(layouts_path))

    def fake_select_layout(
        *,
        layouts_json_file: str,
        selected_layouts_names: list[str],
        select_interactively: bool,
    ) -> list[LayoutConfig]:
        _ = layouts_json_file, select_interactively
        return layouts_selected if selected_layouts_names else layouts_selected

    monkeypatch.setattr(subject, "select_layout", fake_select_layout)

    with pytest.raises(ValueError, match="matched no tabs"):
        subject.run_aoe_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            choose_layouts=None,
            choose_tabs="missing",
            sleep_inbetween=0.1,
            max_tabs=4,
            agent=None,
            model=None,
            provider=None,
            sandbox=None,
            yolo=False,
            cmd=None,
            args=[],
            env=[],
            force=False,
            dry_run=False,
            aoe_bin="aoe",
            tab_command_mode="prompt",
            subsitute_home=False,
            launch=False,
        )


def test_run_aoe_cli_converts_aoe_errors_to_typer_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layouts_path = tmp_path.joinpath("layouts.json")
    layouts_path.write_text("{}", encoding="utf-8")
    layouts_selected: list[LayoutConfig] = [
        {
            "layoutName": "alpha",
            "layoutTabs": [{"tabName": "shared", "startDir": "/a", "command": "echo a"}],
        }
    ]

    monkeypatch.setattr(subject, "find_layout_file", lambda *, layout_path: str(layouts_path))
    monkeypatch.setattr(subject, "select_layout", lambda **kwargs: layouts_selected)

    def fail_run_layouts_via_aoe(**kwargs: object) -> None:
        _ = kwargs
        raise ValueError("boom")

    monkeypatch.setattr(subject, "run_layouts_via_aoe", fail_run_layouts_via_aoe)

    with pytest.raises(typer.Exit) as exc_info:
        subject.run_aoe_cli(
            ctx=_make_context(),
            layouts_file="layouts.json",
            choose_layouts=None,
            choose_tabs=None,
            sleep_inbetween=0.1,
            max_tabs=4,
            agent=None,
            model=None,
            provider=None,
            sandbox=None,
            yolo=False,
            cmd=None,
            args=[],
            env=[],
            force=False,
            dry_run=False,
            aoe_bin="aoe",
            tab_command_mode="prompt",
            subsitute_home=False,
            launch=False,
        )

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "boom" in captured.out
