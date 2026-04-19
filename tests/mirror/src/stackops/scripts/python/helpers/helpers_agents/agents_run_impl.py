

from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.agents_run_impl as run_impl_module


def test_make_prompt_file_writes_context_and_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "prompt123"

    monkeypatch.setattr(run_impl_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(run_impl_module, "randstr", fake_randstr)

    prompt_file = run_impl_module._make_prompt_file(prompt="Do thing", context="Repo facts")

    assert prompt_file == tmp_path / "tmp_results" / "tmp_files" / "agents" / "run_prompt_prompt123.md"
    payload = prompt_file.read_text(encoding="utf-8")
    assert "# Context" in payload
    assert "Repo facts" in payload
    assert "# Prompt" in payload
    assert "Do thing" in payload


def test_build_agent_command_supports_codex_and_rejects_reasoning_for_other_agents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Prompt", encoding="utf-8")

    monkeypatch.setattr(run_impl_module, "system", lambda: "Linux")
    monkeypatch.setattr(run_impl_module, "get_repo_root", lambda _cwd: tmp_path)
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_agents.mcp_install.resolve_agent_launch_prefix",
        lambda **_kwargs: ["prefix", "--flag"],
    )

    codex_command = run_impl_module.build_agent_command(
        agent="codex",
        prompt_file=prompt_file,
        reasoning_effort="high",
    )

    assert "codex exec" in codex_command
    assert 'model_reasoning_effort="high"' in codex_command
    assert f"< {prompt_file}" in codex_command

    pi_command = run_impl_module.build_agent_command(
        agent="pi",
        prompt_file=prompt_file,
        reasoning_effort="none",
    )

    assert "pi --thinking off -p" in pi_command
    assert f"$(cat {prompt_file})" in pi_command

    with pytest.raises(ValueError, match="only supported for --agent codex or --agent pi"):
        run_impl_module.build_agent_command(
            agent="qwen",
            prompt_file=prompt_file,
            reasoning_effort="high",
        )


def test_run_returns_after_edit_when_no_prompt_or_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml_path = tmp_path / "prompts.yaml"
    yaml_path.write_text("default: value\n", encoding="utf-8")
    calls: list[str] = []

    monkeypatch.setattr(run_impl_module, "resolve_prompts_yaml_paths", lambda **_kwargs: [("explicit", yaml_path)])
    monkeypatch.setattr(run_impl_module, "ensure_prompts_yaml_exists", lambda *, yaml_path: False)
    monkeypatch.setattr(run_impl_module, "edit_prompts_yaml", lambda *, yaml_path: calls.append(f"edit:{yaml_path}"))
    monkeypatch.setattr(run_impl_module, "prompts_yaml_format_explanation", lambda *, yaml_paths: "format")
    monkeypatch.setattr(run_impl_module, "resolve_context", lambda **_kwargs: pytest.fail("resolve_context should not run"))
    monkeypatch.setattr(run_impl_module, "_make_prompt_file", lambda **_kwargs: pytest.fail("_make_prompt_file should not run"))

    run_impl_module.run(
        prompt=None,
        agent="codex",
        reasoning_effort=None,
        context=None,
        context_path=None,
        prompts_yaml_path=str(yaml_path),
        context_name=None,
        where="all",
        edit=True,
        show_prompts_yaml_format=False,
    )

    assert calls == [f"edit:{yaml_path}"]
