

from dataclasses import dataclass, field

import pytest

from stackops.cluster.sessions_managers.zellij.zellij_utils import layout_generator as subject
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _make_layout_config() -> LayoutConfig:
    return {
        "layoutName": "RemoteSession",
        "layoutTabs": [
            {"tabName": 'Main "Tab"', "startDir": "/repo", "command": 'python -c "print(\'hello world\')"'},
            {"tabName": "Logs", "startDir": "/var/log", "command": "tail -f app.log"},
        ],
    }


@dataclass(slots=True)
class FakeConsole:
    messages: list[str] = field(default_factory=list)

    def print(self, message: str) -> None:
        self.messages.append(message)



def test_parse_command_falls_back_when_shlex_rejects_input() -> None:
    command, args = subject.LayoutGenerator.parse_command('python "unterminated')

    assert command == "python"
    assert args == ['"unterminated']



def test_validate_tab_config_rejects_blank_runtime_values() -> None:
    invalid_layout: LayoutConfig = {"layoutName": "", "layoutTabs": [{"tabName": "Main", "startDir": "/repo", "command": "python app.py"}]}

    with pytest.raises(ValueError, match="Layout name cannot be empty"):
        subject.LayoutGenerator.validate_tab_config(invalid_layout)



def test_create_tab_section_escapes_names_and_arguments() -> None:
    section = subject.LayoutGenerator.create_tab_section('Main "Tab"', "~", 'python -c "print(\'hello world\')"')

    assert 'tab name="Main \\"Tab\\"" cwd="~"' in section
    assert 'pane command="python"' in section
    assert "args \"-c\" \"print('hello world')\"" in section



def test_create_layout_file_returns_rendered_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = FakeConsole()
    generator = subject.LayoutGenerator()
    layout_config = _make_layout_config()
    monkeypatch.setattr(subject, "console", fake_console)

    layout_content = generator.create_layout_file(layout_config, session_name="remote-session")

    assert fake_console.messages == ["[bold green]✅ Zellij layout content generated[/bold green]"]
    assert 'tab name="Main \\"Tab\\""' in layout_content
    assert 'tab name="Logs"' in layout_content
    assert layout_content.endswith("\n}\n")
