from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl
from stackops.scripts.python.helpers.helpers_agents import agents_skill_stackops_backend
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    AGENT_SKILL_PREVIEW_SIZE_PERCENT,
    build_agent_skill_install_commands,
    parse_requested_skill_names,
    resolve_agent_skill_install_backend,
    SKILL_INSTALL_COMMAND_BACKEND,
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


def test_resolve_agent_skill_install_backend_accepts_stackops_alias() -> None:
    assert resolve_agent_skill_install_backend(backend="stackops") == "stackops"
    assert resolve_agent_skill_install_backend(backend="s") == "stackops"


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


def test_add_skill_dispatches_stackops_backend_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def fake_install_stackops_agent_skills(
        *,
        skill_names: tuple[str, ...],
        skill_folder_names: dict[str, str],
        install_root: Path,
        scope: object,
    ) -> tuple[agents_skill_stackops_backend.StackopsAgentSkillInstallResult, ...]:
        results = (
            agents_skill_stackops_backend.StackopsAgentSkillInstallResult(
                skill_name="stackops",
                source_path=tmp_path / "source" / "stackops",
                target_path=tmp_path / ".agents" / "skills" / "stackops",
            ),
        )
        observed["skill_names"] = skill_names
        observed["skill_folder_names"] = skill_folder_names
        observed["install_root"] = install_root
        observed["scope"] = scope
        return results

    def fake_print_stackops_agent_skill_install_summary(
        *, results: tuple[agents_skill_stackops_backend.StackopsAgentSkillInstallResult, ...]
    ) -> None:
        observed["summary_results"] = results

    monkeypatch.setattr(agents_skill_stackops_backend, "install_stackops_agent_skills", fake_install_stackops_agent_skills)
    monkeypatch.setattr(
        agents_skill_stackops_backend,
        "print_stackops_agent_skill_install_summary",
        fake_print_stackops_agent_skill_install_summary,
    )

    result = agents_skill_impl.add_skill(
        skill_name="stackops,agentops",
        agent="codex",
        scope="local",
        directory=str(tmp_path),
        backend="s",
        yes=True,
    )

    assert result == 0
    assert observed["skill_names"] == ("stackops", "agentops")
    assert observed["skill_folder_names"] == {
        "agentops": "agentops",
        "agent-browser": "agent-browser",
        "agent-skills": "agent-skills",
        "caveman": "caveman",
        "grill-me": "grill-me",
        "last30days": "last30days",
        "stackops": "stackops",
    }
    assert observed["install_root"] == tmp_path.resolve()
    assert observed["scope"] == "local"
    assert observed["summary_results"] == (
        agents_skill_stackops_backend.StackopsAgentSkillInstallResult(
            skill_name="stackops",
            source_path=tmp_path / "source" / "stackops",
            target_path=tmp_path / ".agents" / "skills" / "stackops",
        ),
    )


def test_add_skill_stackops_backend_falls_back_to_bunx(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def fake_install_stackops_agent_skills(
        *,
        skill_names: tuple[str, ...],
        skill_folder_names: dict[str, str],
        install_root: Path,
        scope: object,
    ) -> tuple[agents_skill_stackops_backend.StackopsAgentSkillInstallResult, ...]:
        observed["stackops_skill_names"] = skill_names
        observed["stackops_skill_folder_names"] = skill_folder_names
        observed["stackops_install_root"] = install_root
        observed["stackops_scope"] = scope
        raise agents_skill_stackops_backend.StackopsAgentSkillBackendError("not bundled")

    def fake_print_stackops_skill_install_fallback(*, error: ValueError, fallback_backend: SKILL_INSTALL_COMMAND_BACKEND) -> None:
        observed["fallback_error"] = str(error)
        observed["fallback_backend"] = fallback_backend

    def fake_run_agent_skill_install_commands(*, install_root: Path, commands: tuple[tuple[str, ...], ...]) -> int:
        observed["fallback_install_root"] = install_root
        observed["fallback_commands"] = commands
        return 7

    monkeypatch.setattr(agents_skill_stackops_backend, "install_stackops_agent_skills", fake_install_stackops_agent_skills)
    monkeypatch.setattr(agents_skill_impl, "print_stackops_skill_install_fallback", fake_print_stackops_skill_install_fallback)
    monkeypatch.setattr(agents_skill_impl, "run_agent_skill_install_commands", fake_run_agent_skill_install_commands)

    result = agents_skill_impl.add_skill(
        skill_name="agent-skills",
        agent="codex",
        scope="local",
        directory=str(tmp_path),
        backend="stackops",
        yes=True,
    )

    assert result == 7
    assert observed["stackops_skill_names"] == ("agent-skills",)
    assert observed["stackops_install_root"] == tmp_path.resolve()
    assert observed["stackops_scope"] == "local"
    assert observed["fallback_error"] == "not bundled"
    assert observed["fallback_backend"] == "bunx"
    assert observed["fallback_install_root"] == tmp_path.resolve()
    assert observed["fallback_commands"] == (
        (
            "bunx",
            "skills@latest",
            "add",
            "addyosmani/agent-skills",
            "--yes",
            "--agent",
            "codex",
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
