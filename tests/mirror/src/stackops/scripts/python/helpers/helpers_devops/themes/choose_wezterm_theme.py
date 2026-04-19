

from dataclasses import dataclass
from pathlib import Path
import curses

import pytest

from stackops.scripts.python.helpers.helpers_devops.themes import choose_wezterm_theme as wezterm_module


@dataclass(slots=True)
class FakeStdScr:
    keys: list[int]
    rows: int
    writes: list[str]

    def clear(self) -> None:
        return None

    def getmaxyx(self) -> tuple[int, int]:
        return (self.rows, 80)

    def addstr(self, _y: int, _x: int, text: str, *_attrs: int) -> None:
        self.writes.append(text)

    def getch(self) -> int:
        return self.keys.pop(0)


def test_set_theme_rewrites_wezterm_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path.joinpath(".config", "wezterm", "wezterm.lua")
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """local config = {}\nconfig.color_scheme = 'Old'\nreturn config\n""",
        encoding="utf-8",
    )

    monkeypatch.setattr(wezterm_module.Path, "home", lambda: tmp_path)

    wezterm_module.set_theme("Neon")

    assert config_path.read_text(encoding="utf-8") == """local config = {}\nconfig.color_scheme = 'Neon'\nreturn config"""


def test_main2_skips_theme_update_when_selection_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    selected_themes: list[str] = []

    def fake_choose_from_options(
        multi: bool,
        options: list[str],
        header: str,
        tv: bool,
        msg: str,
    ) -> None:
        _ = (multi, options, header, tv, msg)
        return None

    def fake_set_theme(theme: str) -> None:
        selected_themes.append(theme)

    monkeypatch.setattr(wezterm_module, "choose_from_options", fake_choose_from_options)
    monkeypatch.setattr(wezterm_module, "set_theme", fake_set_theme)

    wezterm_module.main2()

    assert selected_themes == []
    assert "cancelled" in capsys.readouterr().out.lower()


def test_accessory_applies_selected_theme(monkeypatch: pytest.MonkeyPatch) -> None:
    selected_themes: list[str] = []

    def fake_set_theme(theme: str) -> None:
        selected_themes.append(theme)

    monkeypatch.setattr(wezterm_module, "set_theme", fake_set_theme)
    screen = FakeStdScr(keys=[curses.KEY_DOWN, curses.KEY_DOWN, ord("\n")], rows=5, writes=[])

    wezterm_module.accessory(screen)

    assert selected_themes[-1] == wezterm_module.schemes_list[2]
    assert any("Theme 3/" in write for write in screen.writes)
