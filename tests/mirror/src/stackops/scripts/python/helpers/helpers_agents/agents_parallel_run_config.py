from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_config


def test_parallel_yaml_template_uses_reasoning_key_and_runtime_defaults(tmp_path: Path) -> None:
    yaml_path = tmp_path / "custom.parallel.yaml"

    created = agents_parallel_run_config.ensure_parallel_yaml_exists(yaml_path=yaml_path)

    assert created is True
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert yaml_text.startswith("# yaml-language-server: $schema=./custom.parallel.schema.json\n")
    assert "reasoning:" in yaml_text
    assert "reasoning_effort:" not in yaml_text
    assert "job_name: AI_Agents" in yaml_text
    assert "context: no context" in yaml_text
    assert "context_path: null" in yaml_text
    assert "agent_load: 1" in yaml_text
    assert "prompt: go" in yaml_text
    assert "prompt_path: null" in yaml_text
