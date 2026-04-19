

import json
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_gemini as fire_gemini_module
import stackops.utils.accessories as accessories
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, API_SPEC


def _build_ai_spec(*, machine: str, api_key: str | None, model: str | None) -> AI_SPEC:
    api_spec = API_SPEC(api_key=api_key, api_name="primary", api_label="main", api_account="agent@example.com")
    return AI_SPEC(provider="google", model=model, agent="gemini", machine=machine, api_spec=api_spec, reasoning_effort=None)


def test_fire_gemini_local_writes_settings_file_and_quotes_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_path = tmp_path / "prompt with spaces.md"
    prompt_path.write_text("Prompt", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "fixed"

    monkeypatch.setattr(fire_gemini_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(accessories, "randstr", fake_randstr)

    command = fire_gemini_module.fire_gemini(
        ai_spec=_build_ai_spec(machine="local", api_key="secret-token", model="gemini pro"), prompt_path=prompt_path, repo_root=repo_root
    )

    settings_path = tmp_path / "tmp_results" / "tmp_files" / "agents" / "gemini_settings_fixed.json"
    assert settings_path.read_text(encoding="utf-8") == json.dumps({"security": {"auth": {"selectedType": "gemini-api-key"}}}, indent=2)
    assert 'export GEMINI_API_KEY="secret-token"' in command
    assert "--model 'gemini pro'" in command
    assert "--prompt" in command
    assert str(prompt_path) in command


def test_fire_gemini_local_without_api_key_uses_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Prompt", encoding="utf-8")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "warn"

    monkeypatch.setattr(fire_gemini_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(accessories, "randstr", fake_randstr)

    command = fire_gemini_module.fire_gemini(
        ai_spec=_build_ai_spec(machine="local", api_key=None, model=None), prompt_path=prompt_path, repo_root=repo_root
    )

    assert "Warning: No GEMINI_API_KEY provided" in command
    assert "--model" not in command


def test_fire_gemini_docker_requires_api_key_and_uses_repo_relative_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "task.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("Prompt", encoding="utf-8")

    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "docker"

    monkeypatch.setattr(fire_gemini_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(accessories, "randstr", fake_randstr)

    with pytest.raises(AssertionError, match="api_key must be provided"):
        fire_gemini_module.fire_gemini(
            ai_spec=_build_ai_spec(machine="docker", api_key=None, model=None), prompt_path=prompt_path, repo_root=repo_root
        )

    command = fire_gemini_module.fire_gemini(
        ai_spec=_build_ai_spec(machine="docker", api_key="sekret", model=None), prompt_path=prompt_path, repo_root=repo_root
    )

    assert "docker run -it --rm" in command
    assert f'-v "{repo_root}:/workspace/{repo_root.name}"' in command
    assert "--yolo prompts/task.md" in command
    assert 'export GEMINI_API_KEY="sekret"' in command
