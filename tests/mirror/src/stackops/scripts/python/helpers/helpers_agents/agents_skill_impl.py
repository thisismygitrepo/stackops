from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    build_agent_skill_install_commands,
    choose_requested_skill_name,
    parse_requested_skill_agent_targets,
    render_agent_skill_install_script,
)


@dataclass
class SkillRunCapture:
    install_root: Path | None
    commands: tuple[tuple[str, ...], ...] | None


def test_build_caveman_local_command_lets_skills_cli_choose_agents() -> None:
    commands = build_agent_skill_install_commands(skill_names=("caveman",), agent_targets=(), scope="local")

    assert commands == (("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes"),)


def test_build_caveman_global_command_passes_raw_agent_target() -> None:
    commands = build_agent_skill_install_commands(skill_names=("caveman",), agent_targets=("github-copilot",), scope="global")

    assert commands == (("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes", "--global", "--agent", "github-copilot"),)


def test_build_agent_browser_command_passes_multiple_raw_agent_targets() -> None:
    commands = build_agent_skill_install_commands(skill_names=("agent-browser",), agent_targets=("cursor", "codex"), scope="local")

    assert commands == (("bunx", "skills@latest", "add", "vercel-labs/agent-browser", "--yes", "--agent", "cursor", "codex"),)


def test_build_grill_me_command() -> None:
    commands = build_agent_skill_install_commands(skill_names=("grill-me",), agent_targets=(), scope="local")

    assert commands == (("bunx", "skills@latest", "add", "mattpocock/skills/grill-me", "--yes"),)


def test_build_skill_command_rejects_unknown_skill() -> None:
    with pytest.raises(ValueError, match="Skill 'missing' is not recognized"):
        build_agent_skill_install_commands(skill_names=("missing",), agent_targets=(), scope="local")


def test_parse_requested_skill_agent_targets_accepts_comma_separated_values() -> None:
    assert parse_requested_skill_agent_targets(raw_value="codex, github-copilot") == ("codex", "github-copilot")


def test_parse_requested_skill_agent_targets_treats_empty_value_as_autodetect() -> None:
    assert parse_requested_skill_agent_targets(raw_value="") == ()


def test_parse_requested_skill_agent_targets_rejects_empty_entries() -> None:
    with pytest.raises(ValueError, match="Agent targets must be a comma-separated list without empty entries"):
        parse_requested_skill_agent_targets(raw_value="codex,,github-copilot")


def test_render_agent_skill_install_script_quotes_install_root() -> None:
    install_root = Path("/tmp/stackops skill root")
    script = render_agent_skill_install_script(
        install_root=install_root, commands=(("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes"),)
    )

    assert script == "cd '/tmp/stackops skill root'\nbunx skills@latest add JuliusBrussee/caveman --yes\n"


def test_choose_requested_skill_name_uses_fuzzy_picker(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_options: list[tuple[str, ...]] = []

    def fake_choose_from_options(*, options: Iterable[str], msg: str, multi: Literal[False], custom_input: bool, header: str, tv: bool) -> str:
        captured_options.append(tuple(options))
        assert msg == "Choose skill to install"
        assert multi is False
        assert custom_input is False
        assert header == "Agent Skills"
        assert tv is True
        return "grill-me"

    monkeypatch.setattr(agents_skill_impl, "choose_from_options", fake_choose_from_options)

    assert choose_requested_skill_name() == "grill-me"
    assert captured_options == [("agent-browser", "caveman", "grill-me")]


def test_choose_requested_skill_name_rejects_cancelled_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_choose_from_options(*, options: Iterable[str], msg: str, multi: Literal[False], custom_input: bool, header: str, tv: bool) -> None:
        _ = (tuple(options), msg, multi, custom_input, header, tv)
        return None

    monkeypatch.setattr(agents_skill_impl, "choose_from_options", fake_choose_from_options)

    with pytest.raises(ValueError, match="Selection cancelled for agent skill"):
        choose_requested_skill_name()


def test_add_skill_uses_picker_when_skill_name_is_omitted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    capture = SkillRunCapture(install_root=None, commands=None)

    def fake_choose_requested_skill_name() -> str:
        return "grill-me"

    def fake_run_agent_skill_install_commands(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> None:
        capture.install_root = install_root
        capture.commands = tuple(commands)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(agents_skill_impl, "choose_requested_skill_name", fake_choose_requested_skill_name)
    monkeypatch.setattr(agents_skill_impl, "run_agent_skill_install_commands", fake_run_agent_skill_install_commands)

    agents_skill_impl.add_skill(skill_name=None, agent=None, scope="local", directory=None)

    assert capture.install_root == tmp_path
    assert capture.commands == (("bunx", "skills@latest", "add", "mattpocock/skills/grill-me", "--yes"),)
