from pathlib import Path

import pytest

from stackops.settings.yazi.scripts import open_default_app


def test_resolve_targets_prefers_selected_paths(tmp_path: Path) -> None:
    hovered_path = tmp_path / "hovered.txt"
    selected_path = tmp_path / "selected.txt"
    hovered_path.write_text("hovered", encoding="utf-8")
    selected_path.write_text("selected", encoding="utf-8")

    assert open_default_app.resolve_targets(
        [
            open_default_app.HOVERED_MARKER,
            str(hovered_path),
            open_default_app.SELECTED_MARKER,
            str(selected_path),
        ]
    ) == [selected_path.resolve()]


def test_resolve_targets_uses_hovered_path_when_nothing_is_selected(tmp_path: Path) -> None:
    hovered_path = tmp_path / "hovered.txt"
    hovered_path.write_text("hovered", encoding="utf-8")

    assert open_default_app.resolve_targets(
        [
            open_default_app.HOVERED_MARKER,
            str(hovered_path),
            open_default_app.SELECTED_MARKER,
        ]
    ) == [hovered_path.resolve()]


def test_build_default_open_candidates_uses_macos_open(tmp_path: Path) -> None:
    target_path = tmp_path / "document.pdf"
    target_path.write_text("pdf", encoding="utf-8")

    candidates = open_default_app.build_default_open_candidates(target_path, system="darwin")

    assert candidates[0].label == "macOS open"
    assert candidates[0].command == ["open", str(target_path)]


def test_build_default_open_candidates_uses_windows_start_options(tmp_path: Path) -> None:
    target_path = tmp_path / "document.txt"
    target_path.write_text("text", encoding="utf-8")

    candidates = open_default_app.build_default_open_candidates(target_path, system="windows")

    assert [candidate.label for candidate in candidates] == [
        "PowerShell Start-Process",
        "PowerShell Core Start-Process",
        "cmd start",
    ]


def test_build_default_open_candidates_includes_linux_desktop_and_server_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target_path = tmp_path / "document.txt"
    target_path.write_text("text", encoding="utf-8")
    monkeypatch.setattr(open_default_app, "is_wsl", lambda: False)

    candidates = open_default_app.build_default_open_candidates(target_path, system="linux")
    labels = [candidate.label for candidate in candidates]

    assert "xdg-open" in labels
    assert "gio open" in labels
    assert "mimeopen" in labels
    assert "run-mailcap" in labels


def test_open_target_uses_native_windows_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target_path = tmp_path / "document.txt"
    target_path.write_text("text", encoding="utf-8")
    opened_paths: list[str] = []

    monkeypatch.setattr(
        open_default_app.os,
        "startfile",
        lambda path: opened_paths.append(path),
        raising=False,
    )

    assert open_default_app.open_target(target_path, system="windows") == []
    assert opened_paths == [str(target_path)]
