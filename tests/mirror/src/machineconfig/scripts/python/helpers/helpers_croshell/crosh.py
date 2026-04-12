from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import rich.console
import rich.panel
import rich.syntax
import rich.text

import machineconfig.utils.files.read as read_module
from machineconfig.scripts.python.helpers.helpers_croshell import crosh


@dataclass(slots=True)
class FakePanel:
    renderable: object
    title: str
    expand: bool | None = None
    border_style: str | None = None


@dataclass(slots=True)
class FakeText:
    value: str
    justify: str

    def __str__(self) -> str:
        return self.value


class FakeSyntax:
    last_code = ""
    last_lexer = ""

    def __init__(self, code: str, lexer: str) -> None:
        type(self).last_code = code
        type(self).last_lexer = lexer


class FakeConsole:
    printed: list[object] = []

    def print(self, obj: object, style: str | None = None) -> None:
        _ = style
        type(self).printed.append(obj)


def _reset_rich_fakes() -> None:
    FakeConsole.printed = []
    FakeSyntax.last_code = ""
    FakeSyntax.last_lexer = ""


def test_get_read_python_file_pycode_extracts_tail_segment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script_path = tmp_path.joinpath("script.py")
    script_path.write_text(
        "
".join(
            [
                "prefix",
                "except Exception: print(pycode)",
                "middle",
                "except Exception: print(pycode)",
                'print("wanted")',
            ]
        ),
        encoding="utf-8",
    )

    _reset_rich_fakes()
    monkeypatch.setattr(rich.console, "Console", FakeConsole)
    monkeypatch.setattr(rich.panel, "Panel", FakePanel)
    monkeypatch.setattr(rich.syntax, "Syntax", FakeSyntax)

    crosh.get_read_python_file_pycode(path=str(script_path), title="Tail")

    assert FakeSyntax.last_code.strip() == 'print("wanted")'
    assert FakeSyntax.last_lexer == "python"
    assert isinstance(FakeConsole.printed[0], FakePanel)
    assert FakeConsole.printed[0].title == "Tail"


def test_get_read_data_pycode_renders_runtime_reader_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_path = tmp_path.joinpath("data.json")
    data_path.write_text("{}", encoding="utf-8")

    def fake_read_file(path: Path) -> object:
        _ = path
        raise RuntimeError("boom")

    _reset_rich_fakes()
    monkeypatch.setattr(read_module, "read_file", fake_read_file)
    monkeypatch.setattr(rich.console, "Console", FakeConsole)
    monkeypatch.setattr(rich.panel, "Panel", FakePanel)
    monkeypatch.setattr(rich.text, "Text", FakeText)

    crosh.get_read_data_pycode(path=str(data_path))

    assert isinstance(FakeConsole.printed[0], FakePanel)
    panel = FakeConsole.printed[0]
    assert isinstance(panel.renderable, FakeText)
    assert "ERROR READING FILE" in panel.renderable.value
    assert "boom" in panel.renderable.value
