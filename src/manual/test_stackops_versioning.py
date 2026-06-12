from datetime import date

import pytest

from stackops.scripts.python.helpers.helpers_utils.upgrade_packages import (
    format_stackops_display_version,
    get_next_stackops_version,
    parse_stackops_calver,
)


def test_legacy_version_migrates_to_current_calver_month() -> None:
    assert get_next_stackops_version("8.104", today=date(2026, 6, 9)) == "26.6"


def test_same_month_releases_increment_unbounded_release_number() -> None:
    assert get_next_stackops_version("26.6", today=date(2026, 6, 9)) == "26.6.1"
    assert get_next_stackops_version("26.6.500", today=date(2026, 6, 9)) == "26.6.501"


def test_new_month_release_resets_to_month_base_version() -> None:
    assert get_next_stackops_version("26.6.500", today=date(2026, 7, 1)) == "26.7"
    assert get_next_stackops_version("25.12.4", today=date(2026, 1, 1)) == "26.1"


def test_future_month_version_is_rejected_to_avoid_downgrade() -> None:
    with pytest.raises(ValueError, match="later than today's release month"):
        get_next_stackops_version("26.7", today=date(2026, 6, 9))


def test_display_version_keeps_v_prefix_and_canonical_month() -> None:
    assert format_stackops_display_version("26.6") == "v26.6"
    assert format_stackops_display_version("26.6.1") == "v26.6.1"


def test_calver_parser_accepts_tag_style_and_rejects_invalid_months() -> None:
    parsed = parse_stackops_calver("v26.6.500")
    assert parsed is not None
    assert parsed.year == 26
    assert parsed.month == 6
    assert parsed.release == 500
    assert parse_stackops_calver("8.104") is None
