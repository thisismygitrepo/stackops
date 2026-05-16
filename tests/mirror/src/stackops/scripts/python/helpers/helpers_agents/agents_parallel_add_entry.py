from pathlib import Path

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_add_entry


def test_ensure_parallel_yaml_entry_exists_adds_top_level_entry(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "agents" / "parallel.yaml"

    created = agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="demo")

    assert created is True
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert yaml_text.startswith("# yaml-language-server: $schema=./parallel.schema.json\n")
    assert "demo:\n  agent: codex\n" in yaml_text
    assert "reasoning:\n" not in yaml_text
    loaded_yaml = yaml.safe_load(yaml_text)
    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["demo"]["reasoning"] is None
    assert loaded_yaml["demo"]["agent_load"] == 3
    assert loaded_yaml["demo"]["context"] is None
    assert loaded_yaml["demo"]["context_path"] is None
    assert loaded_yaml["demo"]["prompt"] is None
    assert loaded_yaml["demo"]["prompt_path"] is None


def test_ensure_parallel_yaml_entry_exists_adds_top_level_entry_without_rewriting_siblings(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "agents" / "parallel.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        """# yaml-language-server: $schema=./parallel.schema.json

# parallel.yaml used by `agents parallel run-parallel`
existing:
  agent: codex
  prompt: repo
other:
  agent: copilot
""",
        encoding="utf-8",
    )

    created = agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="update-docs")

    assert created is True
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert "existing:\n  agent: codex\n  prompt: repo\n" in yaml_text
    assert "other:\n  agent: copilot\n" in yaml_text
    assert "update-docs:\n  agent: codex\n" in yaml_text
    loaded_yaml = yaml.safe_load(yaml_text)
    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["update-docs"]["job_name"] == "AI_Agents"
    assert loaded_yaml["update-docs"]["agent_load"] == 3
    assert loaded_yaml["update-docs"]["context"] is None
    assert loaded_yaml["update-docs"]["context_path"] is None
    assert loaded_yaml["update-docs"]["prompt"] is None
    assert loaded_yaml["update-docs"]["prompt_path"] is None


def test_ensure_parallel_yaml_entry_exists_is_noop_for_existing_entry(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "agents" / "parallel.yaml"

    agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="demo")
    created = agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="demo")

    assert created is False


def test_add_parallel_yaml_entry_generates_unique_placeholder_names(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "agents" / "parallel.yaml"

    first_entry_name = agents_parallel_add_entry.add_parallel_yaml_entry(yaml_path=yaml_path, entry_name=None)
    second_entry_name = agents_parallel_add_entry.add_parallel_yaml_entry(yaml_path=yaml_path, entry_name=None)

    assert first_entry_name == "entryExample"
    assert second_entry_name == "entryExample_2"
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert "entryExample:\n  agent: codex\n" in yaml_text
    assert "entryExample_2:\n  agent: codex\n" in yaml_text


def test_ensure_parallel_yaml_entry_exists_rejects_dotted_names(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "agents" / "parallel.yaml"

    with pytest.raises(ValueError, match="flat top-level YAML keys without dots"):
        agents_parallel_add_entry.ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name="docs.update")


def test_upsert_parallel_yaml_entry_updates_existing_named_entry(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "agents" / "parallel.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        """# yaml-language-server: $schema=./parallel.schema.json

# parallel.yaml used by `agents parallel run-parallel`
docs:
  agent: codex
  prompt: old prompt
other:
  agent: copilot
""",
        encoding="utf-8",
    )

    agents_parallel_add_entry.upsert_parallel_yaml_entry(
        yaml_path=yaml_path,
        entry_name="docs",
        entry_values={
            "agent": "codex",
            "model": None,
            "reasoning": "high",
            "provider": "openai",
            "host": "local",
            "context": None,
            "context_path": "./context.md",
            "separator": "\\n@-@\\n",
            "agent_load": 5,
            "prompt": None,
            "prompt_path": "./prompt.md",
            "prompt_name": None,
            "job_name": "docs",
            "join_prompt_and_context": False,
            "run": False,
            "output_path": None,
            "agents_dir": None,
            "interactive": False,
        },
    )

    loaded_yaml = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["docs"]["reasoning"] == "high"
    assert loaded_yaml["docs"]["prompt_path"] == "./prompt.md"
    assert loaded_yaml["docs"]["agent_load"] == 5
    assert loaded_yaml["other"]["agent"] == "copilot"
