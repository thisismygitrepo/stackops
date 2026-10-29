from stackops.utils.schemas.layouts.layout_types import TabArrangement


def infer_arrangement_from_origins(origins: list[tuple[int, int]]) -> TabArrangement:
    if len({top for _left, top in origins}) == 1:
        return "columns"
    if len({left for left, _top in origins}) == 1:
        return "rows"
    return "grid"
