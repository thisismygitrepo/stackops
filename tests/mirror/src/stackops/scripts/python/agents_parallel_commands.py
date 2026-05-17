import pytest

import stackops.scripts.python.agents_parallel_commands as agents_parallel_commands


def test_agents_create_passes_save_as_yaml_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_values: list[bool] = []

    def fake_impl(
        *,
        agent: str,
        model: str | None,
        agent_load: int,
        context: str | None,
        context_path: str | None,
        separator: str,
        prompt: str | None,
        prompt_path: str | None,
        prompt_name: str | None,
        job_name: str | None,
        join_prompt_and_context: bool,
        run: bool,
        output_path: str | None,
        agents_dir: str | None,
        save_as_yaml: bool,
        host: str,
        reasoning: str | None,
        provider: str | None,
        interactive: bool,
        stutter_max: float,
    ) -> None:
        _ = (
            agent,
            model,
            agent_load,
            context,
            context_path,
            separator,
            prompt,
            prompt_path,
            prompt_name,
            job_name,
            join_prompt_and_context,
            run,
            output_path,
            agents_dir,
            host,
            reasoning,
            provider,
            interactive,
            stutter_max,
        )
        captured_values.append(save_as_yaml)

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_agents.agents_impl.agents_create", fake_impl)

    agents_parallel_commands.agents_create(
        agent="codex",
        model=None,
        reasoning_effort=None,
        provider="openai",
        host="local",
        context=None,
        context_path="context.md",
        separator="\\n@-@\\n",
        agent_load=3,
        stutter_max=4.5,
        prompt=None,
        prompt_path="prompt.md",
        prompt_name=None,
        job_name="docs",
        join_prompt_and_context=False,
        run=False,
        output_path=None,
        agents_dir=None,
        save_as_yaml=True,
        interactive=False,
    )

    assert captured_values == [True]
