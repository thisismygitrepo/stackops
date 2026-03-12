from collections import deque


def _maybe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _pane_int(pane: dict[str, object], key: str) -> int:
    value = _maybe_int(pane.get(key))
    return value if value is not None else 0


def selectable_panes_for_tab(
    panes: list[dict[str, object]],
    tab_position: int,
) -> list[dict[str, object]]:
    relevant = [
        pane
        for pane in panes
        if pane.get("tab_position") == tab_position
        and pane.get("is_selectable")
        and not pane.get("is_plugin")
        and not pane.get("exited")
        and not pane.get("is_suppressed")
    ]
    relevant.sort(key=_pane_sort_key)
    return relevant


def _pane_sort_key(pane: dict[str, object]) -> tuple[int, int, int, int]:
    return (
        _pane_int(pane, "tab_position"),
        _pane_int(pane, "pane_y"),
        _pane_int(pane, "pane_x"),
        _pane_int(pane, "id"),
    )


def _rect_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> int:
    return max(0, min(end_a, end_b) - max(start_a, start_b))


def _pane_neighbor(
    source_pane: dict[str, object],
    panes: list[dict[str, object]],
    direction: str,
) -> int | None:
    source_id = _maybe_int(source_pane.get("id"))
    source_x = _pane_int(source_pane, "pane_x")
    source_y = _pane_int(source_pane, "pane_y")
    source_cols = _pane_int(source_pane, "pane_columns")
    source_rows = _pane_int(source_pane, "pane_rows")
    source_right = source_x + source_cols
    source_bottom = source_y + source_rows

    best_id: int | None = None
    best_key: tuple[int, int, int] | None = None
    for candidate in panes:
        candidate_id = _maybe_int(candidate.get("id"))
        if candidate_id is None or candidate_id == source_id:
            continue
        candidate_x = _pane_int(candidate, "pane_x")
        candidate_y = _pane_int(candidate, "pane_y")
        candidate_cols = _pane_int(candidate, "pane_columns")
        candidate_rows = _pane_int(candidate, "pane_rows")
        candidate_right = candidate_x + candidate_cols
        candidate_bottom = candidate_y + candidate_rows

        if direction == "right":
            overlap = _rect_overlap(source_y, source_bottom, candidate_y, candidate_bottom)
            if overlap <= 0 or candidate_x < source_right:
                continue
            gap = candidate_x - source_right
        elif direction == "left":
            overlap = _rect_overlap(source_y, source_bottom, candidate_y, candidate_bottom)
            if overlap <= 0 or candidate_right > source_x:
                continue
            gap = source_x - candidate_right
        elif direction == "down":
            overlap = _rect_overlap(source_x, source_right, candidate_x, candidate_right)
            if overlap <= 0 or candidate_y < source_bottom:
                continue
            gap = candidate_y - source_bottom
        elif direction == "up":
            overlap = _rect_overlap(source_x, source_right, candidate_x, candidate_right)
            if overlap <= 0 or candidate_bottom > source_y:
                continue
            gap = source_y - candidate_bottom
        else:
            continue

        candidate_key = (gap, -overlap, candidate_id)
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_id = candidate_id
    return best_id


def focus_path_to_pane(
    panes: list[dict[str, object]],
    target_pane: dict[str, object],
) -> list[str] | None:
    target_id = _maybe_int(target_pane.get("id"))
    if target_id is None:
        return None
    focused_pane = next((pane for pane in panes if pane.get("is_focused")), None)
    focused_id = _maybe_int(focused_pane.get("id")) if focused_pane is not None else None
    if focused_id is None:
        return None
    if focused_id == target_id:
        return []

    panes_by_id = {
        pane_id: pane
        for pane in panes
        if (pane_id := _maybe_int(pane.get("id"))) is not None
    }
    queue: deque[tuple[int, list[str]]] = deque([(focused_id, [])])
    visited = {focused_id}
    directions = ("left", "right", "up", "down")

    while queue:
        current_id, path = queue.popleft()
        current_pane = panes_by_id.get(current_id)
        if current_pane is None:
            continue
        for direction in directions:
            neighbor_id = _pane_neighbor(current_pane, panes, direction)
            if neighbor_id is None or neighbor_id in visited:
                continue
            next_path = path + [direction]
            if neighbor_id == target_id:
                return next_path
            visited.add(neighbor_id)
            queue.append((neighbor_id, next_path))
    return None
