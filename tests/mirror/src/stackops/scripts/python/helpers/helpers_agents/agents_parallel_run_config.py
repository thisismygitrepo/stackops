from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_config
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ParallelCreateValues


def _base_values() -> ParallelCreateValues:
    return ParallelCreateValues(
        agent="codex",
        model="gpt-test",
        reasoning_effort="high",
        provider="openai",
        host="local",
        context=None,
        context_path="./context.md",
        separator="\\n@-@\\n",
        agent_load=3,
        prompt=None,
        prompt_path="./prompt.md",
        prompt_name=None,
        job_name="base_job",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        interactive=False,
    )


def test_resolve_parallel_yaml_paths_includes_repo_first_for_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr("stackops.utils.accessories.get_repo_root", fake_get_repo_root)

    locations = agents_parallel_run_config.resolve_parallel_yaml_paths(parallel_yaml_path=None, where="all")

    assert locations[0] == ("repo", tmp_path / ".stackops" / "parallel.yaml")


def test_resolve_parallel_yaml_paths_repo_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr("stackops.utils.accessories.get_repo_root", fake_get_repo_root)

    assert agents_parallel_run_config.resolve_parallel_yaml_paths(parallel_yaml_path=None, where="repo") == [
        ("repo", tmp_path / ".stackops" / "parallel.yaml")
    ]


def test_resolve_parallel_yaml_paths_rejects_repo_outside_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_repo_root(_path: Path) -> None:
        return None

    monkeypatch.setattr("stackops.utils.accessories.get_repo_root", fake_get_repo_root)

    with pytest.raises(ValueError, match="--where repo requires running inside a git repository"):
        agents_parallel_run_config.resolve_parallel_yaml_paths(parallel_yaml_path=None, where="repo")


def test_ensure_parallel_yaml_exists_creates_sibling_schema(tmp_path: Path) -> None:
    yaml_path = tmp_path / "custom.parallel.yaml"

    created = agents_parallel_run_config.ensure_parallel_yaml_exists(yaml_path=yaml_path)

    assert created
    schema_path = tmp_path / "custom.parallel.schema.json"
    assert schema_path.is_file()
    assert yaml_path.read_text(encoding="utf-8").startswith(
        "# yaml-language-server: $schema=./custom.parallel.schema.json\n"
    )
    assert '"StackOps parallel.yaml"' in schema_path.read_text(encoding="utf-8")


def test_merge_parallel_create_values_applies_overrides_and_decodes_separator() -> None:
    overrides = ParallelCreateValues(
        agent="copilot",
        model=None,
        reasoning_effort=None,
        provider=None,
        host=None,
        context="override context",
        context_path=None,
        separator="\\n###\\n",
        agent_load=5,
        prompt="override prompt",
        prompt_path=None,
        prompt_name=None,
        job_name="override_job",
        join_prompt_and_context=True,
        output_path="./layout.json",
        agents_dir="./agents",
        interactive=True,
    )

    resolved = agents_parallel_run_config.merge_parallel_create_values(base=_base_values(), overrides=overrides)

    assert resolved.agent == "copilot"
    assert resolved.model == "gpt-test"
    assert resolved.context == "override context"
    assert resolved.separator == "\n###\n"
    assert resolved.agent_load == 5
    assert resolved.prompt == "override prompt"
    assert resolved.prompt_path == "./prompt.md"
    assert resolved.job_name == "override_job"
    assert resolved.join_prompt_and_context
    assert resolved.output_path == "./layout.json"
    assert resolved.agents_dir == "./agents"
    assert resolved.interactive


def test_merge_parallel_create_values_rejects_non_positive_agent_load() -> None:
    overrides = ParallelCreateValues(
        agent=None,
        model=None,
        reasoning_effort=None,
        provider=None,
        host=None,
        context=None,
        context_path=None,
        separator=None,
        agent_load=0,
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name=None,
        join_prompt_and_context=None,
        output_path=None,
        agents_dir=None,
        interactive=None,
    )

    with pytest.raises(ValueError, match="agent_load must be a positive integer"):
        agents_parallel_run_config.merge_parallel_create_values(base=_base_values(), overrides=overrides)
