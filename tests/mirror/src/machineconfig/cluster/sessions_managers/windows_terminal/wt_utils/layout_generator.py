from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.cluster.sessions_managers.windows_terminal.wt_utils import layout_generator as layout_module
from machineconfig.utils.schemas.layouts.layout_types import TabConfig


def _make_tabs() -> list[TabConfig]:
    return [
        {
            "tabName": "API Server",
            "startDir": "~",
            "command": 'python api.py --label "two words"',
        },
        {
            "tabName": "Worker",
            "startDir": "~/jobs",
            "command": "python worker.py",
        },
    ]


def test_parse_command_falls_back_when_shell_quoting_is_invalid() -> None:
    command, args = layout_module.WTLayoutGenerator.parse_command('python "unterminated')

    assert command == "python"
    assert args == ['"unterminated']


def test_create_tab_command_expands_home_and_quotes_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(layout_module.Path, "home", lambda: tmp_path)

    command = layout_module.WTLayoutGenerator.create_tab_command(
        tab_name="API Server",
        cwd="~/project dir",
        command='python api.py --label "two words"',
        is_first_tab=True,
    )

    assert command.startswith(f'-d "{tmp_path}/project dir"')
    assert '--title "API Server"' in command
    assert '"python api.py --label two words"' in command
    assert "new-tab" not in command


def test_generate_wt_command_and_script_include_session_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(layout_module.WTLayoutGenerator, "generate_random_suffix", staticmethod(lambda length=8: "fixed123"))

    generator = layout_module.WTLayoutGenerator()
    command = generator.generate_wt_command(
        tabs=_make_tabs(),
        window_name="Work Space",
        maximized=True,
        focus=False,
    )
    script = generator.create_wt_script(_make_tabs(), session_name="SessionOne")

    assert command.startswith('wt --maximized -w "Work Space"')
    assert "--focus" not in command
    assert "; new-tab" in command
    assert "# Generated on fixed123" in script
    assert "wt --focus -w SessionOne" in script


@pytest.mark.parametrize(
    ("tab_name", "start_dir", "command"),
    [
        ("", "~/repo", "python app.py"),
        ("tab", "", "python app.py"),
        ("tab", "~/repo", ""),
    ],
)
def test_validate_tab_config_rejects_blank_required_fields(
    tab_name: str,
    start_dir: str,
    command: str,
) -> None:
    with pytest.raises(ValueError):
        layout_module.WTLayoutGenerator.validate_tab_config(
            [
                {
                    "tabName": tab_name,
                    "startDir": start_dir,
                    "command": command,
                }
            ]
        )


def test_generate_split_pane_command_uses_split_pane_separator() -> None:
    generator = layout_module.WTLayoutGenerator()

    command = generator.generate_split_pane_command(_make_tabs(), window_name="SplitWindow")

    assert command.startswith("wt -w SplitWindow")
    assert "; split-pane" in command
    assert command.count("--title") == 2
