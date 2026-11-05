import sys

import pytest

from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper import FireJobArgs, extract_kwargs


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["fire", "run", "job.py", "hello", "--script"], {}),
        (["fire", "run", "job.py", "hello", "--script", "--frozen", "--"], {}),
        (["fire", "run", "job.py", "hello", "--frozen", "--", "--a=1", "--b", "two", "--c"], {"a": 1, "b": "two", "c": True}),
    ],
)
def test_only_arguments_after_separator_reach_the_function(monkeypatch: pytest.MonkeyPatch, argv: list[str], expected: dict[str, object]) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    assert extract_kwargs(FireJobArgs(mode="run")) == expected
