from pathlib import Path

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import update_docs, update_installer, update_test, workflows_yaml


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    loaded_yaml: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded_yaml, dict)

    yaml_mapping: dict[str, object] = {}
    for raw_key, raw_value in loaded_yaml.items():
        assert isinstance(raw_key, str)
        yaml_mapping[raw_key] = raw_value
    return yaml_mapping


def _require_entry(yaml_mapping: dict[str, object], key: str) -> dict[str, object]:
    raw_entry = yaml_mapping[key]
    assert isinstance(raw_entry, dict)

    entry: dict[str, object] = {}
    for raw_key, raw_value in raw_entry.items():
        assert isinstance(raw_key, str)
        entry[raw_key] = raw_value
    return entry


def test_write_workflows_to_yaml_upserts_self_workflows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    parallel_yaml_path = tmp_path / ".stackops" / "parallel.yaml"
    parallel_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    parallel_yaml_path.write_text(
        """custom:
  agent: copilot
  prompt: keep
update-docs:
  prompt: stale
""",
        encoding="utf-8",
    )

    python_context = "src/stackops/a.py\n@-@\nsrc/stackops/b.py"
    docs_context = "docs/cli/agents.md\n@-@\ndocs/api/index.md"

    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    def fake_update_installer() -> None:
        update_installer.agents_create_impl(
            agent="codex",
            model=None,
            agent_load=10,
            context=None,
            context_path=str(tmp_path / "src" / "stackops" / "jobs" / "installer" / "installer_data.json"),
            separator=update_installer.UPDATE_INSTALLER_SEPARATOR,
            prompt="installer prompt",
            prompt_path=None,
            prompt_name=None,
            job_name=update_installer.DEFAULT_INSTALLER_JOB_NAME,
            join_prompt_and_context=False,
            output_path=str(tmp_path / ".ai" / "agents" / update_installer.DEFAULT_INSTALLER_JOB_NAME / "layout.json"),
            agents_dir=str(tmp_path / ".ai" / "agents" / update_installer.DEFAULT_INSTALLER_JOB_NAME),
            host="local",
            reasoning_effort=None,
            provider=None,
            interactive=False,
        )

    def fake_update_test() -> None:
        update_test.agents_create_impl(
            agent="codex",
            model=None,
            agent_load=10,
            context=python_context,
            context_path=None,
            separator="\n@-@\n",
            prompt=update_test.UPDATE_TEST_PROMPT,
            prompt_path=None,
            prompt_name=None,
            job_name=update_test.DEFAULT_TEST_JOB_NAME,
            join_prompt_and_context=False,
            output_path=str(tmp_path / ".ai" / "agents" / update_test.DEFAULT_TEST_JOB_NAME / "layout.json"),
            agents_dir=str(tmp_path / ".ai" / "agents" / update_test.DEFAULT_TEST_JOB_NAME),
            host="local",
            reasoning_effort=None,
            provider=None,
            interactive=False,
        )

    def fake_update_docs() -> None:
        update_docs.agents_create_impl(
            agent="codex",
            model=None,
            agent_load=10,
            context=docs_context,
            context_path=None,
            separator="\n@-@\n",
            prompt=update_docs.UPDATE_DOCS_PROMPT,
            prompt_path=None,
            prompt_name=None,
            job_name=update_docs.DEFAULT_DOCS_JOB_NAME,
            join_prompt_and_context=False,
            output_path=str(tmp_path / ".ai" / "agents" / update_docs.DEFAULT_DOCS_JOB_NAME / "layout.json"),
            agents_dir=str(tmp_path / ".ai" / "agents" / update_docs.DEFAULT_DOCS_JOB_NAME),
            host="local",
            reasoning_effort=None,
            provider=None,
            interactive=False,
        )

    monkeypatch.setattr(workflows_yaml, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(update_installer, "update_installer", fake_update_installer)
    monkeypatch.setattr(update_test, "update_test", fake_update_test)
    monkeypatch.setattr(update_docs, "update_docs", fake_update_docs)

    written_path = workflows_yaml.write_workflows_to_yaml()

    assert written_path == parallel_yaml_path
    assert (tmp_path / ".stackops" / "parallel.schema.json").is_file()
    assert parallel_yaml_path.read_text(encoding="utf-8").startswith(
        "# yaml-language-server: $schema=./parallel.schema.json\n"
    )
    yaml_mapping = _read_yaml_mapping(parallel_yaml_path)
    assert yaml_mapping["custom"] == {"agent": "copilot", "prompt": "keep"}

    update_test_entry = _require_entry(yaml_mapping=yaml_mapping, key="update-test")
    assert "context" not in update_test_entry
    assert "context_path" not in update_test_entry
    assert update_test_entry["agents_dir"] == "./.ai/agents/updateTests"
    assert update_test_entry["output_path"] == "./.ai/agents/updateTests/layout.json"
    assert update_test_entry["agent_load"] == 10
    assert update_test_entry["prompt"] == update_test.UPDATE_TEST_PROMPT

    update_docs_entry = _require_entry(yaml_mapping=yaml_mapping, key="update-docs")
    assert update_docs_entry["prompt"] == update_docs.UPDATE_DOCS_PROMPT
    assert "context" not in update_docs_entry
    assert "context_path" not in update_docs_entry

    update_installer_entry = _require_entry(yaml_mapping=yaml_mapping, key="update-installer")
    assert update_installer_entry["context_path"] == "./src/stackops/jobs/installer/installer_data.json"
