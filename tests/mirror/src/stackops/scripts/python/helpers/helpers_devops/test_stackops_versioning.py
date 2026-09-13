from datetime import date

import pytest

from stackops.scripts.python.helpers.helpers_devops.stackops_versioning import get_next_stackops_version, parse_stackops_calver


@pytest.mark.parametrize(
    ("current", "today", "expected"),
    [
        ("26.6", date(2026, 6, 9), "26.6.1"),
        ("26.6.500", date(2026, 6, 9), "26.6.501"),
        ("26.6.500", date(2026, 7, 1), "26.7"),
        ("25.12.4", date(2026, 1, 1), "26.1"),
    ],
)
def test_next_release(current: str, today: date, expected: str) -> None:
    assert get_next_stackops_version(current_version=current, today=today) == expected


@pytest.mark.parametrize("current", ["26.7", "27.1", "26.7.99"])
def test_future_month_version_is_rejected_to_avoid_downgrade(current: str) -> None:
    with pytest.raises(ValueError, match="later than today's release month"):
        get_next_stackops_version(current_version=current, today=date(2026, 6, 9))


@pytest.mark.parametrize("version", ["8.104", "v26.6", "26.06", "26.6.0", "26.13", "26.6a1", "26.6.1.2", " 26.6", "２６.6"])
def test_calver_parser_rejects_noncanonical_versions(version: str) -> None:
    with pytest.raises(ValueError, match="Invalid StackOps CalVer"):
        parse_stackops_calver(version=version)
