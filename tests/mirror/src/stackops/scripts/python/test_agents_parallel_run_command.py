from collections.abc import Sequence

import pytest
import typer
from typer.testing import CliRunner

from stackops.scripts.python.agents_parallel_run_command import run_parallel
from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_impl
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import PARALLEL_RUNS_SOURCE, ParallelCreateValues


@pytest.mark.parametrize(
    ("extra_arguments", "expected_overrides"),
    [
        ((), (None, None, None)),
        (("--join-prompt-context", "true", "--run", "true", "--interactive", "true"), (True, True, True)),
        (("-j", "true", "-R", "true", "-i", "true"), (True, True, True)),
        (("--join-prompt-context", "false", "--run", "false", "--interactive", "false"), (False, False, False)),
        (("--run", "false"), (None, False, None)),
    ],
)
def test_boolean_options_preserve_yaml_or_override_either_state(
    extra_arguments: Sequence[str],
    expected_overrides: tuple[bool | None, bool | None, bool | None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded_overrides: list[tuple[bool | None, bool | None, bool | None]] = []

    def capture_run(
        *,
        config_name: str | None,
        parallel_yaml_path: str | None,
        source: PARALLEL_RUNS_SOURCE,
        overrides: ParallelCreateValues,
        edit: bool,
        add_entry: bool,
        show_parallel_yaml_format: bool,
    ) -> None:
        assert config_name == "sample"
        assert parallel_yaml_path is None
        assert source == "all"
        assert edit is False
        assert add_entry is False
        assert show_parallel_yaml_format is False
        forwarded_overrides.append((overrides.join_prompt_and_context, overrides.run, overrides.interactive))

    monkeypatch.setattr(agents_parallel_run_impl, "run_parallel_from_yaml", capture_run)
    app = typer.Typer(add_completion=False)
    app.command()(run_parallel)

    result = CliRunner().invoke(app, ["sample", *extra_arguments])

    assert result.exit_code == 0, result.output
    assert forwarded_overrides == [expected_overrides]


@pytest.mark.parametrize(
    "arguments",
    [
        ("--run",),
        ("--run", "maybe"),
        ("--run=yes",),
        ("--interactive", "1"),
        ("--no-run",),
        ("--no-interactive",),
        ("--no-join-prompt-context",),
        ("--joined-prompt-context", "true"),
    ],
)
def test_boolean_options_reject_missing_values_invalid_values_and_paired_forms(arguments: Sequence[str], monkeypatch: pytest.MonkeyPatch) -> None:
    forwarded_calls: list[ParallelCreateValues] = []

    def capture_run(
        *,
        config_name: str | None,
        parallel_yaml_path: str | None,
        source: PARALLEL_RUNS_SOURCE,
        overrides: ParallelCreateValues,
        edit: bool,
        add_entry: bool,
        show_parallel_yaml_format: bool,
    ) -> None:
        forwarded_calls.append(overrides)

    monkeypatch.setattr(agents_parallel_run_impl, "run_parallel_from_yaml", capture_run)
    app = typer.Typer(add_completion=False)
    app.command()(run_parallel)

    result = CliRunner().invoke(app, ["sample", *arguments])

    assert result.exit_code == 2, result.output
    assert forwarded_calls == []
