from __future__ import annotations

import machineconfig.utils.path_extended as path_extended


def test_validate_name_replaces_disallowed_characters() -> None:
    assert path_extended.validate_name("bad name:/?.txt") == "bad_name_.txt"
def test_split_appends_separator_to_right_side() -> None:
    left, right = path_extended.PathExtended("root/alpha/beta").split(at="alpha", sep=1)

    assert str(left) == "root"
    assert str(right) == "alpha/beta"
