from pathlib import Path
from typing import cast

import pytest

from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks import fire_crush
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC


def _build_ai_spec(*, machine: str, api_key: str | None, model: str | None, provider: str | None) -> AI_SPEC:
    return cast(
        AI_SPEC,
        {
            "machine": machine,
            "api_spec": {"api_key": api_key},
            "model": model,
            "provider": provider,
        },
    )


def test_fire_crush_local_command_uses_prompt_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"

    command = fire_crush.fire_crush(
        _build_ai_spec(machine="local", api_key=None, model=None, provider=None),
        prompt_path,
        repo_root,
    )

    assert f"crush run {prompt_path}" in command


def test_fire_crush_docker_writes_config_file_and_maps_google_to_gemini(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"
    template_path = tmp_path / "fire_crush.json"
    template_path.write_text('{"api":"{api_key}","model":"{model}","provider":"{provider}"}', encoding="utf-8")
    fake_home = tmp_path / "home"

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        assert path_reference == "fire_crush.json"
        return template_path

    monkeypatch.setattr(fire_crush, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(fire_crush.Path, "home", classmethod(lambda cls: fake_home))

    command = fire_crush.fire_crush(
        _build_ai_spec(machine="docker", api_key="secret-key", model="gemini-2.5", provider="google"),
        prompt_path,
        repo_root,
    )

    config_files = list((fake_home / "tmp_results" / "tmp_files").glob("crush_*.json"))
    assert len(config_files) == 1
    config_text = config_files[0].read_text(encoding="utf-8")
    assert '"api":"secret-key"' in config_text
    assert '"model":"gemini-2.5"' in config_text
    assert '"provider":"gemini"' in config_text
    assert str(config_files[0]) in command
    assert f"./{prompt_path.relative_to(repo_root)}" in command


def test_fire_crush_docker_requires_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_path = repo_root / "prompts" / "agent.md"
    template_path = tmp_path / "fire_crush.json"
    template_path.write_text('{"api":"{api_key}","provider":"{provider}"}', encoding="utf-8")

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        assert path_reference == "fire_crush.json"
        return template_path

    monkeypatch.setattr(fire_crush, "get_path_reference_path", fake_get_path_reference_path)

    with pytest.raises(ValueError, match="Provider must be specified for Crush agent"):
        fire_crush.fire_crush(
            _build_ai_spec(machine="docker", api_key="secret-key", model=None, provider=None),
            prompt_path,
            repo_root,
        )
