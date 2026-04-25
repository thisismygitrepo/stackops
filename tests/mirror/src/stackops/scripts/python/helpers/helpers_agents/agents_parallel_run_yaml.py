import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_yaml


def test_parse_parallel_create_values_accepts_standard_create_keys() -> None:
    raw_entry: dict[str, object] = {
        "agent": "codex",
        "model": "gpt-test",
        "reasoning_effort": "high",
        "provider": "openai",
        "host": "local",
        "context": None,
        "context_path": "./context.md",
        "separator": "\\n@-@\\n",
        "agent_load": 2,
        "prompt": None,
        "prompt_path": "./prompt.md",
        "prompt_name": None,
        "job_name": "demo",
        "join_prompt_and_context": False,
        "output_path": "./layout.json",
        "agents_dir": "./agents",
        "interactive": False,
    }

    parsed = agents_parallel_run_yaml.parse_parallel_create_values(raw_entry=raw_entry, entry_name="demo")

    assert parsed.agent == "codex"
    assert parsed.model == "gpt-test"
    assert parsed.reasoning_effort == "high"
    assert parsed.provider == "openai"
    assert parsed.host == "local"
    assert parsed.context_path == "./context.md"
    assert parsed.separator == "\\n@-@\\n"
    assert parsed.agent_load == 2
    assert parsed.prompt_path == "./prompt.md"
    assert parsed.job_name == "demo"
    assert parsed.join_prompt_and_context is False
    assert parsed.output_path == "./layout.json"
    assert parsed.agents_dir == "./agents"
    assert parsed.interactive is False


def test_parse_parallel_create_values_rejects_unknown_keys() -> None:
    raw_entry: dict[str, object] = {"agent": "codex", "unknown": True}

    with pytest.raises(ValueError, match="Unknown keys in parallel run 'demo': unknown"):
        agents_parallel_run_yaml.parse_parallel_create_values(raw_entry=raw_entry, entry_name="demo")


def test_select_parallel_create_values_from_locations_uses_named_repo_entry() -> None:
    yaml_entries: list[tuple[str, object]] = [
        ("repo", {"docs": {"update": {"agent": "codex", "prompt": "repo"}}}),
        ("private", {"docs": {"update": {"agent": "copilot", "prompt": "private"}}}),
    ]

    _entry_name, parsed = agents_parallel_run_yaml.select_parallel_create_values_from_locations(
        yaml_entries=yaml_entries,
        requested_name="docs.update",
    )

    assert parsed.agent == "codex"
    assert parsed.prompt == "repo"


def test_select_parallel_create_values_from_locations_rejects_missing_named_entry() -> None:
    yaml_entries: list[tuple[str, object]] = [("repo", {"docs": {"update": {"agent": "codex"}}})]

    with pytest.raises(ValueError, match="Parallel run 'missing' was not found in parallel YAML"):
        agents_parallel_run_yaml.select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name="missing")
