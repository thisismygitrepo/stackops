from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml import (
    parse_parallel_create_values,
    select_parallel_create_values,
    select_parallel_create_values_from_locations,
)
from stackops.utils.options_utils import tv_options


def test_select_parallel_create_values_accepts_multiple_interactive_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_data: dict[str, object] = {
        "alpha": {"context": "alpha context", "job_name": "alpha"},
        "beta": {"context": "beta context", "job_name": "beta"},
    }

    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, object], extension: str | None, multi: bool, preview_size_percent: float
    ) -> list[str] | str | None:
        assert set(options_to_preview_mapping) == {"alpha", "beta"}
        assert extension == "yaml"
        assert multi is True
        assert preview_size_percent == 70.0
        return ["alpha", "beta"]

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    selected_entries = select_parallel_create_values(raw_data=raw_data, requested_name=None)

    assert tuple(selected_name for selected_name, _base_values in selected_entries) == ("alpha", "beta")
    assert selected_entries[0][1].context == "alpha context"
    assert selected_entries[1][1].context == "beta context"


def test_parse_parallel_create_values_accepts_backend() -> None:
    parsed = parse_parallel_create_values(raw_entry={"backend": "herdr"}, entry_name="alpha")

    assert parsed.backend == "herdr"


def test_parse_parallel_create_values_accepts_aoe_backend() -> None:
    parsed = parse_parallel_create_values(raw_entry={"backend": "aoe"}, entry_name="alpha")

    assert parsed.backend == "aoe"


def test_select_parallel_create_values_from_locations_preserves_multi_choice_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml_entries = [
        ("repo", tmp_path / "repo.yaml", {"alpha": {"context": "alpha context", "job_name": "alpha"}}),
        ("private", tmp_path / "private.yaml", {"beta": {"context": "beta context", "job_name": "beta"}}),
    ]

    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, object], extension: str | None, multi: bool, preview_size_percent: float
    ) -> list[str] | str | None:
        assert set(options_to_preview_mapping) == {"repo:alpha", "private:beta"}
        assert extension == "yaml"
        assert multi is True
        assert preview_size_percent == 70.0
        return ["private:beta", "repo:alpha"]

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    selected_entries = select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name=None)

    assert tuple(selected_name for selected_name, _base_values in selected_entries) == ("beta", "alpha")
    assert selected_entries[0][1].context == "beta context"
    assert selected_entries[1][1].context == "alpha context"


def test_select_parallel_create_values_from_locations_keeps_requested_name_single(tmp_path: Path) -> None:
    yaml_entries = [("repo", tmp_path / "repo.yaml", {"alpha": {"context": "alpha context", "job_name": "alpha"}})]

    selected_entries = select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name="alpha")

    assert tuple(selected_name for selected_name, _base_values in selected_entries) == ("alpha",)
    assert selected_entries[0][1].context == "alpha context"
