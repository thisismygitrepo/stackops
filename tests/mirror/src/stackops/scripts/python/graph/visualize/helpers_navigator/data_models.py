from __future__ import annotations

from stackops.scripts.python.graph.visualize.helpers_navigator.data_models import ArgumentInfo


def test_argument_info_default_flag_lists_are_not_shared() -> None:
    first = ArgumentInfo(name="verbose", is_required=False, is_flag=True)
    second = ArgumentInfo(name="quiet", is_required=False, is_flag=True)

    first.long_flags.append("--verbose")
    first.short_flags.append("-v")

    assert second.long_flags == []
    assert second.short_flags == []
