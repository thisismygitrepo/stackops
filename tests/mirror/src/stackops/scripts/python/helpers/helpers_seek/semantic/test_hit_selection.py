from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.hit_selection import limit_distinct_hits
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticHit


def _hit(path: str, start_line: int, end_line: int) -> SemanticHit:
    return SemanticHit(
        path=Path(path),
        start_line=start_line,
        end_line=end_line,
        focus_line=start_line,
        metric="score",
        value=0.5,
        content="",
    )


def test_overlapping_windows_in_the_same_file_keep_only_the_best_ranked() -> None:
    best = _hit("/repo/a.py", 10, 20)
    overlapping_tail = _hit("/repo/a.py", 20, 30)
    overlapping_inside = _hit("/repo/a.py", 12, 14)

    assert limit_distinct_hits(hits=[best, overlapping_tail, overlapping_inside], limit=10) == [best]


def test_adjacent_windows_and_other_files_are_kept_in_ranked_order() -> None:
    first = _hit("/repo/a.py", 10, 20)
    other_file = _hit("/repo/b.py", 10, 20)
    adjacent = _hit("/repo/a.py", 21, 30)

    assert limit_distinct_hits(hits=[first, other_file, adjacent], limit=10) == [first, other_file, adjacent]


def test_limit_counts_distinct_hits_after_overlap_removal() -> None:
    first = _hit("/repo/a.py", 1, 5)
    duplicate = _hit("/repo/a.py", 3, 8)
    second = _hit("/repo/a.py", 40, 45)
    third = _hit("/repo/a.py", 80, 85)

    assert limit_distinct_hits(hits=[first, duplicate, second, third], limit=2) == [first, second]
