import json
from pathlib import Path

import pytest

from stackops.scripts.python.ai import initai
from stackops.scripts.python.helpers.helpers_agents import agents_skill_stackops_backend


def _create_agentops_skill_source(*, root: Path) -> Path:
    source_root = root / "bundled-skills"
    agentops_source = source_root / "agentops"
    agentops_source.joinpath("references").mkdir(parents=True)
    agentops_source.joinpath("SKILL.md").write_text("latest AgentOps skill\n", encoding="utf-8")
    agentops_source.joinpath("references", "workflow.md").write_text("latest workflow\n", encoding="utf-8")
    return source_root


def test_add_ai_configs_copies_latest_agentops_skill_and_tracks_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = _create_agentops_skill_source(root=tmp_path)
    repo_root = tmp_path / "repository"
    target_skill_path = repo_root / ".agents" / "skills" / "agentops" / "SKILL.md"
    target_skill_path.parent.mkdir(parents=True)
    target_skill_path.write_text("stale\n", encoding="utf-8")

    def resolve_source_root(*, source_root: Path | None) -> Path:
        assert source_root is None
        return tmp_path / "bundled-skills"

    monkeypatch.setattr(
        agents_skill_stackops_backend,
        "resolve_stackops_agent_skill_source_root",
        resolve_source_root,
    )

    result = initai.add_ai_configs(
        repo_root=repo_root,
        frameworks=("codex",),
        include_common_scaffold=False,
        add_all_touched_configs_to_gitignore=True,
        add_vscode_task=False,
        add_private_config=False,
        add_instructions=False,
        add_agentops_skill=True,
    )

    target_reference_path = target_skill_path.parent / "references" / "workflow.md"
    expected_skill_content = source_root.joinpath("agentops", "SKILL.md").read_text(encoding="utf-8")
    assert target_skill_path.read_text(encoding="utf-8") == expected_skill_content
    assert target_reference_path.read_text(encoding="utf-8") == "latest workflow\n"
    assert result.plan.add_agentops_skill is True
    assert {change.path for change in result.artifact_changes} >= {
        Path(".agents/skills/agentops/SKILL.md"),
        Path(".agents/skills/agentops/references/workflow.md"),
    }
    assert repo_root.joinpath(".gitignore").read_text(encoding="utf-8").splitlines() == [
        ".agents/skills/agentops/SKILL.md",
        ".agents/skills/agentops/references/workflow.md",
    ]


def test_add_ai_configs_agentops_opt_out_preserves_existing_skill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repository"
    target_skill_path = repo_root / ".agents" / "skills" / "agentops" / "SKILL.md"
    target_skill_path.parent.mkdir(parents=True)
    target_skill_path.write_text("existing customization\n", encoding="utf-8")

    def reject_source_resolution(*, source_root: Path | None) -> Path:
        raise AssertionError(f"AgentOps source must not be resolved when disabled: {source_root}")

    monkeypatch.setattr(
        agents_skill_stackops_backend,
        "resolve_stackops_agent_skill_source_root",
        reject_source_resolution,
    )

    result = initai.add_ai_configs(
        repo_root=repo_root,
        frameworks=("codex",),
        include_common_scaffold=False,
        add_all_touched_configs_to_gitignore=False,
        add_vscode_task=False,
        add_private_config=False,
        add_instructions=False,
        add_agentops_skill=False,
    )

    assert target_skill_path.read_text(encoding="utf-8") == "existing customization\n"
    assert result.plan.add_agentops_skill is False
    assert result.artifact_changes == ()


def test_add_ai_configs_writes_pi_ten_retry_policy(tmp_path: Path) -> None:
    repo_root = tmp_path / "repository"
    repo_root.mkdir()

    initai.add_ai_configs(
        repo_root=repo_root,
        frameworks=("pi",),
        include_common_scaffold=False,
        add_all_touched_configs_to_gitignore=False,
        add_vscode_task=False,
        add_private_config=True,
        add_instructions=False,
        add_agentops_skill=False,
    )

    settings = json.loads(repo_root.joinpath(".pi", "settings.json").read_text(encoding="utf-8"))
    assert settings["retry"] == {
        "enabled": True,
        "maxRetries": 10,
        "baseDelayMs": 2_000,
        "provider": {
            "maxRetries": 0,
            "maxRetryDelayMs": 60_000,
        },
    }


def test_add_ai_configs_writes_omp_ten_retry_policy(tmp_path: Path) -> None:
    repo_root = tmp_path / "repository"
    repo_root.mkdir()

    initai.add_ai_configs(
        repo_root=repo_root,
        frameworks=("omp",),
        include_common_scaffold=False,
        add_all_touched_configs_to_gitignore=False,
        add_vscode_task=False,
        add_private_config=True,
        add_instructions=False,
        add_agentops_skill=False,
    )

    assert repo_root.joinpath(".omp", "config.yml").read_text(encoding="utf-8") == """retry:
  enabled: true
  maxRetries: 10
  baseDelayMs: 500
  maxDelayMs: 300000
"""
