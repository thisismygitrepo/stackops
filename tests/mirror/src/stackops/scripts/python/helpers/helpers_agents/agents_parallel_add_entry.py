from pathlib import Path

import yaml

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_add_entry


def test_ensure_parallel_yaml_entry_exists_adds_top_level_entry(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "parallel.yaml"

    created = agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="demo")

    assert created is True
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert yaml_text.startswith("# yaml-language-server: $schema=./parallel.schema.json\n")
    assert "demo:\n  agent: codex\n" in yaml_text
    assert "reasoning:\n" not in yaml_text
    loaded_yaml = yaml.safe_load(yaml_text)
    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["demo"]["reasoning"] == "high"


def test_ensure_parallel_yaml_entry_exists_adds_nested_entry_without_rewriting_siblings(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "parallel.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        """# yaml-language-server: $schema=./parallel.schema.json

# parallel.yaml used by `agents parallel run-parallel`
docs:
  existing:
    agent: codex
    prompt: repo
other:
  agent: copilot
""",
        encoding="utf-8",
    )

    created = agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="docs.update")

    assert created is True
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert "docs:\n  existing:\n    agent: codex\n    prompt: repo\n  update:\n    agent: codex\n" in yaml_text
    assert "other:\n  agent: copilot\n" in yaml_text
    loaded_yaml = yaml.safe_load(yaml_text)
    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["docs"]["update"]["job_name"] == "AI_Agents"


def test_ensure_parallel_yaml_entry_exists_is_noop_for_existing_entry(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "parallel.yaml"

    agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="demo")
    created = agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="demo")

    assert created is False


def test_add_parallel_yaml_entry_generates_unique_placeholder_names(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "parallel.yaml"

    first_entry_name = agents_parallel_add_entry.add_parallel_yaml_entry(yaml_path=yaml_path, entry_name=None)
    second_entry_name = agents_parallel_add_entry.add_parallel_yaml_entry(yaml_path=yaml_path, entry_name=None)

    assert first_entry_name == "new_entry"
    assert second_entry_name == "new_entry_2"
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert "new_entry:\n  agent: codex\n" in yaml_text
    assert "new_entry_2:\n  agent: codex\n" in yaml_text