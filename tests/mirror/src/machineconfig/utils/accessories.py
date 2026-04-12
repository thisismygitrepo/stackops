from __future__ import annotations

import string
from datetime import datetime, timezone
from pathlib import Path

import pytest

from machineconfig.utils.accessories import (
    display_with_flashy_style,
    get_repr,
    get_repo_root,
    human_friendly_dict,
    pprint,
    randstr,
    split_list,
    split_timeframe,
)


def _find_repo_root(start: Path) -> Path:
    for candidate in start.resolve().parents:
        if candidate.joinpath("pyproject.toml").is_file():
            return candidate
    raise AssertionError("repo root not found")


def test_randstr_respects_requested_character_sets() -> None:
    lowercase_value = randstr(length=64, lower=True, upper=False, digits=False, punctuation=False, safe=False, noun=False)
    digits_value = randstr(length=64, lower=False, upper=False, digits=True, punctuation=False, safe=False, noun=False)
    safe_value = randstr(length=16, lower=False, upper=False, digits=False, punctuation=False, safe=True, noun=False)

    assert len(lowercase_value) == 64
    assert set(lowercase_value) <= set(string.ascii_lowercase)
    assert len(digits_value) == 64
    assert set(digits_value) <= set(string.digits)
    assert safe_value != ""
    assert set(safe_value) <= set(string.ascii_letters + string.digits + "-_")


def test_split_timeframe_requires_exactly_one_strategy() -> None:
    with pytest.raises(ValueError):
        split_timeframe(start_dt="2024-01-01T00:00:00", end_dt="2024-01-01T00:10:00", resolution_ms=1000, to=None, every_ms=None)

    with pytest.raises(ValueError):
        split_timeframe(start_dt="2024-01-01T00:00:00", end_dt="2024-01-01T00:10:00", resolution_ms=1000, to=2, every_ms=300000)


def test_split_timeframe_splits_fixed_count_with_resolution_gap() -> None:
    result = split_timeframe(start_dt="2024-01-01T00:00:00", end_dt="2024-01-01T00:10:00", resolution_ms=1000, to=2, every_ms=None)

    assert result == [
        (datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, 0, 4, 59, tzinfo=timezone.utc)),
        (datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc), datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc)),
    ]


def test_split_timeframe_splits_by_interval_until_end() -> None:
    result = split_timeframe(start_dt="2024-01-01T00:00:00", end_dt="2024-01-01T00:05:00", resolution_ms=1000, to=None, every_ms=120000)

    assert result == [
        (datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, 0, 1, 59, tzinfo=timezone.utc)),
        (datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc), datetime(2024, 1, 1, 0, 3, 59, tzinfo=timezone.utc)),
        (datetime(2024, 1, 1, 0, 4, tzinfo=timezone.utc), datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc)),
    ]


def test_split_list_requires_exactly_one_strategy() -> None:
    with pytest.raises(ValueError):
        split_list(sequence=[1, 2, 3], every=None, to=None)

    with pytest.raises(ValueError):
        split_list(sequence=[1, 2, 3], every=1, to=3)


def test_split_list_supports_fixed_size_and_target_chunk_count() -> None:
    assert split_list(sequence=[1, 2, 3, 4, 5], every=2, to=None) == [[1, 2], [3, 4], [5]]
    assert split_list(sequence=[1, 2, 3, 4, 5], every=None, to=2) == [[1, 2, 3], [4, 5]]
    assert split_list(sequence=[], every=2, to=None) == []


def test_get_repr_formats_values_with_optional_quotes() -> None:
    assert get_repr(obj={"alpha": "beta", "count": "3"}, sep=" | ", justify=0, quotes=False) == "alpha = beta | count = 3"
    assert get_repr(obj={"alpha": "beta"}, sep="\n", justify=0, quotes=True) == "alpha = 'beta'"


def test_human_friendly_dict_formats_supported_runtime_values() -> None:
    result = human_friendly_dict(d={"ratio": 1.234, "enabled": True, "disabled": False, "timestamp_ms": 1704067200000, "raw": "keep-me"})

    assert result == {"ratio": "1.23", "enabled": "✓", "disabled": "✗", "timestamp_ms": "2024-01-01 00:00", "raw": "keep-me"}


def test_get_repo_root_finds_repository_and_rejects_non_repo(tmp_path: Path) -> None:
    expected_repo_root = _find_repo_root(start=Path(__file__))

    assert get_repo_root(path=Path(__file__)) == expected_repo_root
    assert get_repo_root(path=tmp_path) is None


def test_rich_helpers_render_without_error(capsys: pytest.CaptureFixture[str]) -> None:
    pprint(obj={"name": "value"}, title="Mirror")
    display_with_flashy_style(msg="https://example.com/share", title="Share")

    captured = capsys.readouterr()
    assert "https://example.com/share" in captured.out
    assert "Share" in captured.out
