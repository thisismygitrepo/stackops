from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_yaml
from stackops.utils.options_utils import tv_options


def test_parse_parallel_create_values_accepts_reasoning_key() -> None:
    raw_entry: dict[str, object] = {
        "agent": "codex",
        "model": "gpt-test",
        "reasoning": "high",
        "provider": "openai",
        "host": "local",
        "context": None,
        "context_path": "./context.md",
        "separator": "\\n@-@\\n",
        "agent_load": 2,
        "stagger_max": 1.5,
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
    assert parsed.stagger_max == 1.5
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
    yaml_entries: list[agents_parallel_run_yaml.ParallelYamlEntry] = [
        ("repo", Path("/tmp/repo/.stackops/agents/parallel.yaml"), {"docs_update": {"agent": "codex", "prompt": "repo"}}),
        ("private", Path("/tmp/private/parallel.yaml"), {"docs_update": {"agent": "copilot", "prompt": "private"}}),
    ]

    _entry_name, parsed = agents_parallel_run_yaml.select_parallel_create_values_from_locations(
        yaml_entries=yaml_entries, requested_name="docs_update"
    )

    assert parsed.agent == "codex"
    assert parsed.prompt == "repo"


def test_select_parallel_create_values_from_locations_rejects_missing_named_entry() -> None:
    yaml_entries: list[agents_parallel_run_yaml.ParallelYamlEntry] = [
        ("repo", Path("/tmp/repo/.stackops/agents/parallel.yaml"), {"docs_update": {"agent": "codex"}})
    ]

    with pytest.raises(ValueError, match="Parallel run 'missing' was not found in parallel YAML"):
        agents_parallel_run_yaml.select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name="missing")


def test_select_parallel_create_values_from_locations_preview_shows_source_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    yaml_entries: list[agents_parallel_run_yaml.ParallelYamlEntry] = [
        ("repo", Path("/tmp/repo/.stackops/agents/parallel.yaml"), {"docs_update": {"agent": "codex", "prompt": "repo"}}),
        ("private", Path("/tmp/private/parallel.yaml"), {"docs_update": {"agent": "copilot", "prompt": "private"}}),
    ]
    captured_options: dict[str, str] = {}
    captured_preview_size_percent: float | None = None

    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float
    ) -> str:
        nonlocal captured_preview_size_percent
        assert extension == "yaml"
        assert multi is False
        captured_options.update(options_to_preview_mapping)
        captured_preview_size_percent = preview_size_percent
        return "repo:docs_update"

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    _entry_name, parsed = agents_parallel_run_yaml.select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name=None)

    assert captured_preview_size_percent == agents_parallel_run_yaml.PARALLEL_RUN_PREVIEW_SIZE_PERCENT
    assert "source_yaml: /tmp/repo/.stackops/agents/parallel.yaml" in captured_options["repo:docs_update"]
    assert "prompt: repo" in captured_options["repo:docs_update"]
    assert parsed.agent == "codex"


def test_select_parallel_create_values_from_locations_rejects_dotted_names() -> None:
    yaml_entries: list[agents_parallel_run_yaml.ParallelYamlEntry] = [
        ("repo", Path("/tmp/repo/.stackops/agents/parallel.yaml"), {"docs_update": {"agent": "codex"}})
    ]

    with pytest.raises(ValueError, match="flat top-level YAML keys without dots"):
        agents_parallel_run_yaml.select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name="docs.update")
