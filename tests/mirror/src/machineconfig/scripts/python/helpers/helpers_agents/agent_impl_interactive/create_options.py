from dataclasses import dataclass
from typing import cast, get_args

import pytest

from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive import create_options


@dataclass(frozen=True, slots=True)
class _Support:
    efforts: tuple[create_options.ReasoningEffort, ...]


def test_provider_options_for_agent_use_agent_specific_restrictions() -> None:
    all_providers = cast(tuple[create_options.PROVIDER, ...], get_args(create_options.PROVIDER))

    assert create_options._provider_options_for_agent("codex") == ("openai",)
    assert create_options._provider_options_for_agent("gemini") == ("google",)
    assert create_options._provider_options_for_agent("copilot") == all_providers


@pytest.mark.parametrize("raw_value", ["0", "-1", "abc"])
def test_require_positive_int_value_rejects_invalid_numbers(raw_value: str) -> None:
    with pytest.raises(TypeError, match='Expected "agent_load" to be a positive integer'):
        create_options._require_positive_int_value(selected_values={"agent_load": raw_value}, key="agent_load")


def test_collect_create_options_form_selection_parses_textual_form(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_reasoning_support(*, agent: create_options.AGENTS) -> _Support:
        assert agent == "codex"
        return _Support(efforts=("low", "medium"))

    review_options = create_options._build_review_option_labels(
        agent="codex",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        host="local",
        model=None,
        agent_load=3,
        job_name="job",
        reasoning_effort=None,
        provider=None,
    )

    def fake_use_textual_options_form(*, options: create_options.TextualOptionMap) -> create_options.SelectedOptionMap:
        assert review_options["provider"] in options
        return {
            review_options["join_prompt_and_context"]: True,
            review_options["output_path"]: "/tmp/layout.json",
            review_options["agents_dir"]: "/tmp/agents",
            review_options["host"]: "docker",
            review_options["model"]: "gpt-5.4",
            review_options["agent_load"]: "7",
            review_options["job_name"]: "job-7",
            review_options["reasoning_effort"]: "medium",
            review_options["provider"]: "openai",
        }

    monkeypatch.setattr(create_options, "reasoning_support", fake_reasoning_support)
    monkeypatch.setattr(create_options, "use_textual_options_form", fake_use_textual_options_form)

    result = create_options._collect_create_options_form_selection(
        agent="codex",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        host="local",
        model=None,
        agent_load=3,
        job_name="job",
        reasoning_effort=None,
        provider=None,
    )

    assert result.join_prompt_and_context is True
    assert result.output_path == "/tmp/layout.json"
    assert result.agents_dir == "/tmp/agents"
    assert result.host == "docker"
    assert result.model == "gpt-5.4"
    assert result.agent_load == 7
    assert result.job_name == "job-7"
    assert result.reasoning_effort == "medium"
    assert result.provider == "openai"


def test_collect_create_options_form_selection_wraps_cancelled_form(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_reasoning_support(*, agent: create_options.AGENTS) -> _Support:
        assert agent == "codex"
        return _Support(efforts=("low",))

    def fake_use_textual_options_form(*, options: create_options.TextualOptionMap) -> create_options.SelectedOptionMap:
        raise RuntimeError("cancelled")

    monkeypatch.setattr(create_options, "reasoning_support", fake_reasoning_support)
    monkeypatch.setattr(create_options, "use_textual_options_form", fake_use_textual_options_form)

    with pytest.raises(ValueError, match="Selection cancelled for create options"):
        create_options._collect_create_options_form_selection(
            agent="codex",
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            host="local",
            model=None,
            agent_load=3,
            job_name="job",
            reasoning_effort=None,
            provider=None,
        )


def test_collect_reviewed_create_options_drops_unsupported_reasoning_and_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_reasoning_efforts: list[create_options.ReasoningEffort | None] = []
    captured_providers: list[create_options.PROVIDER | None] = []

    def fake_reasoning_support(*, agent: create_options.AGENTS) -> _Support:
        assert agent == "codex"
        return _Support(efforts=("low",))

    def fake_collect_create_options_form_selection(
        *,
        agent: create_options.AGENTS,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        host: create_options.HOST,
        model: str | None,
        agent_load: int,
        job_name: str,
        reasoning_effort: create_options.ReasoningEffort | None,
        provider: create_options.PROVIDER | None,
    ) -> create_options._CreateOptionsFormSelection:
        assert agent == "codex"
        assert join_prompt_and_context is False
        assert output_path is None
        assert agents_dir is None
        assert host == "local"
        assert model is None
        assert agent_load == 3
        assert job_name == "job"
        captured_reasoning_efforts.append(reasoning_effort)
        captured_providers.append(provider)
        return create_options._CreateOptionsFormSelection(
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            host="local",
            model=None,
            agent_load=3,
            job_name="job",
            reasoning_effort=None,
            provider=None,
        )

    monkeypatch.setattr(create_options, "reasoning_support", fake_reasoning_support)
    monkeypatch.setattr(create_options, "_collect_create_options_form_selection", fake_collect_create_options_form_selection)

    result = create_options.collect_reviewed_create_options(
        agent="codex",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        host="local",
        model=None,
        agent_load=3,
        job_name="job",
        reasoning_effort=cast(create_options.ReasoningEffort, "high"),
        provider=cast(create_options.PROVIDER, "google"),
    )

    assert captured_reasoning_efforts == [None]
    assert captured_providers == [None]
    assert result.reasoning_effort is None
    assert result.provider is None
