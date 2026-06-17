from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    AGENT_SKILL_PREVIEW_SIZE_PERCENT,
    build_agent_skill_install_commands,
    parse_requested_skill_names,
    supported_agent_skill_names,
)
from stackops.utils.options_utils import tv_options


def test_recently_added_open_source_skill_names_are_supported() -> None:
    assert {"agent-skills", "last30days"} <= set(supported_agent_skill_names())


def test_parse_requested_skill_names_accepts_comma_separated_values() -> None:
    assert parse_requested_skill_names(raw_value="agent-skills,last30days") == ("agent-skills", "last30days")


def test_parse_requested_skill_names_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="Duplicate skill names"):
        parse_requested_skill_names(raw_value="agent-skills,last30days,agent-skills")


def test_agent_skills_builds_skills_cli_install_command() -> None:
    commands = build_agent_skill_install_commands(
        skill_names=("agent-skills",), agent_targets=("codex",), scope="global", backend="bunx", yes=False
    )

    assert commands == (
        (
            "bunx",
            "skills@latest",
            "add",
            "addyosmani/agent-skills",
            "--global",
            "--agent",
            "codex",
        ),
    )


def test_add_skill_installs_multiple_interactive_choices(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, object], extension: str | None, multi: bool, preview_size_percent: float
    ) -> list[str]:
        assert {"agent-skills", "last30days"} <= set(options_to_preview_mapping)
        assert extension == "json"
        assert multi is True
        assert preview_size_percent == AGENT_SKILL_PREVIEW_SIZE_PERCENT
        return ["agent-skills", "last30days"]

    observed: dict[str, object] = {}

    def fake_run_agent_skill_install_commands(*, install_root: Path, commands: tuple[tuple[str, ...], ...]) -> int:
        observed["install_root"] = install_root
        observed["commands"] = commands
        return 7

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)
    monkeypatch.setattr(agents_skill_impl, "run_agent_skill_install_commands", fake_run_agent_skill_install_commands)

    result = agents_skill_impl.add_skill(
        skill_name=None,
        agent="codex,copilot",
        scope="global",
        directory=str(tmp_path),
        backend="bunx",
        yes=True,
    )

    assert result == 7
    assert observed["install_root"] == tmp_path.resolve()
    assert observed["commands"] == (
        (
            "bunx",
            "skills@latest",
            "add",
            "addyosmani/agent-skills",
            "--yes",
            "--global",
            "--agent",
            "codex",
            "copilot",
        ),
        (
            "bunx",
            "skills@latest",
            "add",
            "mvanhorn/last30days-skill",
            "--yes",
            "--global",
            "--agent",
            "codex",
            "copilot",
        ),
    )


def test_last30days_builds_npx_skills_cli_install_command() -> None:
    commands = build_agent_skill_install_commands(
        skill_names=("last30days",), agent_targets=("codex",), scope="global", backend="npx", yes=True
    )

    assert commands == (
        (
            "npx",
            "skills@latest",
            "add",
            "mvanhorn/last30days-skill",
            "--yes",
            "--global",
            "--agent",
            "codex",
        ),
    )
