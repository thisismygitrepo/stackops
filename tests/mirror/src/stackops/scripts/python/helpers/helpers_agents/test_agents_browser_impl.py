from collections.abc import Sequence
from pathlib import Path

import pytest
import typer

from stackops.scripts.python.helpers.helpers_agents import agents_browser_impl


def test_install_browser_tech_prepares_pinchtab_binary_skill_and_guide(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    installer_names: list[str | None] = []
    commands: list[tuple[tuple[str, ...], Path]] = []

    def capture_installer(
        which: str | None, group: bool, interactive: bool, explore: bool, update: bool, version: str | None, ctx: typer.Context | None
    ) -> None:
        assert group is False
        assert interactive is False
        assert explore is False
        assert update is True
        assert version is None
        assert ctx is None
        installer_names.append(which)

    def capture_command(*, command: Sequence[str], cwd: Path) -> None:
        commands.append((tuple(command), cwd))

    monkeypatch.setattr(agents_browser_impl, "BROWSER_TECH_ROOT", tmp_path)
    monkeypatch.setattr("stackops.utils.installer_utils.installer_cli.main_installer_cli", capture_installer)
    monkeypatch.setattr(agents_browser_impl, "_run_required_command", capture_command)

    result = agents_browser_impl.install_browser_tech(which="pinchtab", agent="codex", backend="bunx")

    install_root = tmp_path.joinpath("pinchtab")
    skill_command = ("bunx", "skills@latest", "add", "pinchtab/pinchtab", "--skill", "pinchtab", "--agent", "codex", "--yes")
    assert installer_names == ["pinchtab"]
    assert commands == [(skill_command, install_root)]
    assert result.which == "pinchtab"
    assert result.install_root == install_root
    assert result.commands == (skill_command,)
    assert result.guide_paths == (install_root.joinpath("pinchtab.md"),)
    assert "pinchtab daemon install" in result.guide_paths[0].read_text(encoding="utf-8")
    assert result.mcp_servers == ()
