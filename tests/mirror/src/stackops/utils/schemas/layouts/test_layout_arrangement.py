import pytest

from stackops.utils.schemas.layouts.layout_arrangement import infer_arrangement_from_origins
from stackops.utils.schemas.layouts.layout_types import TabArrangement


@pytest.mark.parametrize(
    ("origins", "expected"),
    [
        ([(0, 0), (40, 0), (80, 0)], "columns"),
        ([(0, 0), (0, 20)], "rows"),
        ([(0, 0), (40, 0), (0, 20), (40, 20)], "grid"),
        ([(0, 0), (60, 0), (0, 20)], "grid"),
    ],
)
def test_infer_arrangement_from_origins(origins: list[tuple[int, int]], expected: TabArrangement) -> None:
    assert infer_arrangement_from_origins(origins=origins) == expected
