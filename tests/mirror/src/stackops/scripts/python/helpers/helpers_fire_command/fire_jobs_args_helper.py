from __future__ import annotations

from dataclasses import dataclass
import sys

import pytest

from stackops.scripts.python.helpers.helpers_fire_command import fire_jobs_args_helper


@dataclass(frozen=True, slots=True)
class ContextLike:
    args: list[str]


def test_convert_value_type_handles_scalars_and_lists() -> None:
    assert fire_jobs_args_helper._convert_value_type("2") == 2
    assert fire_jobs_args_helper._convert_value_type("3.5") == 3.5
    assert fire_jobs_args_helper._convert_value_type("true") is True
    assert fire_jobs_args_helper._convert_value_type("off") is False
    assert fire_jobs_args_helper._convert_value_type("none") is None
    assert fire_jobs_args_helper._convert_value_type("1,2.5,false,text") == [1, 2.5, False, "text"]


def test_extract_kwargs_parses_fire_style_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prog", "--count=3", "--debug", "--name", "alex", "--items=1,2,false", "--", "--switch"])

    result = fire_jobs_args_helper.extract_kwargs(fire_jobs_args_helper.FireJobArgs())

    assert result == {"count": 3, "debug": True, "name": "alex", "items": [1, 2, False], "switch": True}


def test_parse_fire_args_from_argv_and_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["prog", "fire", "--", "run", "--count=2"])

    assert fire_jobs_args_helper.parse_fire_args_from_argv() == "run --count=2"
    assert fire_jobs_args_helper.parse_fire_args_from_context(ContextLike(args=["--", "run", "--count=2"])) == "run --count=2"
    assert fire_jobs_args_helper.parse_fire_args_from_context(ContextLike(args=[])) == ""
