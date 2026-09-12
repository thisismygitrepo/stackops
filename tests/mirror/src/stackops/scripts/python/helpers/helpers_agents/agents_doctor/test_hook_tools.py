from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_doctor import hook_tools


def test_path_tools_do_not_claim_activation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_which(command: str, *, path: str) -> str | None:
        calls.append(command)
        assert path == str(tmp_path)
        return str(tmp_path / command) if command in ("headroom", "tk") else None

    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(hook_tools.shutil, "which", fake_which)
    output = StringIO()
    hook_tools.render_hook_tools(console=Console(file=output, width=180))
    rendered = output.getvalue()
    assert calls == ["headroom", "tk", "rtk"]
    assert "headroom" in rendered and "tk" in rendered
    assert "Available on PATH; activation not established" in rendered
    assert "PATH presence alone does not mean a tool is active" in rendered


def test_no_known_tools_omits_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str, *, path: str) -> None:
        assert command in ("headroom", "tk", "rtk")
        assert path == str(tmp_path)

    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(hook_tools.shutil, "which", fake_which)
    output = StringIO()
    hook_tools.render_hook_tools(console=Console(file=output))
    assert output.getvalue() == ""


def test_path_symlink_to_protected_binary_is_excluded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "headroom").symlink_to(Path.home() / "dotfiles/headroom")
    calls: list[str] = []

    def fake_which(command: str, *, path: str) -> None:
        calls.append(command)
        assert path == str(tmp_path)

    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(hook_tools.shutil, "which", fake_which)
    output = StringIO()
    hook_tools.render_hook_tools(console=Console(file=output))
    assert calls == ["tk", "rtk"]
    assert "protected or unreadable" in output.getvalue()
