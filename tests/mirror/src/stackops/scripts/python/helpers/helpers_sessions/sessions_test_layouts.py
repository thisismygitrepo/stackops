from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
from typing import cast

import pytest

from stackops.scripts.python.helpers.helpers_sessions import sessions_test_layouts as subject


def test_build_test_layouts_returns_expected_layouts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_dir = tmp_path / "workspace"
    home_dir = tmp_path / "home"
    base_dir.mkdir()
    home_dir.mkdir()
    monkeypatch.setattr(subject.Path, "home", lambda: home_dir)

    layouts = subject.build_test_layouts(base_dir=base_dir)

    assert [layout["layoutName"] for layout in layouts] == [
        "test-layout-alpha",
        "test-layout-beta",
        "test-layout-gamma",
        "test-layout-delta",
    ]
    assert [len(layout["layoutTabs"]) for layout in layouts] == [6, 10, 14, 18]
    assert subject.count_tabs_in_layouts(layouts) == 48

    alpha_first_tab = layouts[0]["layoutTabs"][0]
    beta_first_tab = layouts[1]["layoutTabs"][0]
    assert alpha_first_tab["startDir"] == str(base_dir.resolve())
    assert beta_first_tab["startDir"] == str(home_dir.resolve())
    assert str(Path(sys.executable).resolve()) in alpha_first_tab["command"]
    assert "test-layout-alpha_01" in alpha_first_tab["command"]
    assert "test-layout-beta_01" in beta_first_tab["command"]


def test_join_command_uses_windows_quoting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    join_command = cast(
        Callable[[list[str]], str],
        getattr(subject, "_join_command"),
    )
    parts = ["python.exe", "-c", "two words"]
    monkeypatch.setattr(subject.platform, "system", lambda: "Windows")

    assert join_command(parts) == subprocess.list2cmdline(parts)
