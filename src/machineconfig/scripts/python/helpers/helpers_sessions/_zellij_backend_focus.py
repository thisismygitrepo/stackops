from collections import deque


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
    tab_position = pane.get("tab_position", 0)
    pane_y = pane.get("pane_y", 0)
    pane_x = pane.get("pane_x", 0)
    pane_id = pane.get("id", 0)
    return (
        int(tab_position) if isinstance(tab_position, int) else 0,
        int(pane_y) if isinstance(pane_y, int) else 0,
        int(pane_x) if isinstance(pane_x, int) else 0,
        int(pane_id) if isinstance(pane_id, int) else 0,
    )


def _rect_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> int:
    return max(0, min(end_a, end_b) - max(start_a, start_b))


def _pane_neighbor(
    source_pane: dict[str, object],
    panes: list[dict[str, object]],
    direction: str,
) -> int | None:
    source_x = int(source_pane.get("pane_x", 0))
    source_y = int(source_pane.get("pane_y", 0))
    source_cols = int(source_pane.get("pane_columns", 0))
    source_rows = int(source_pane.get("pane_rows", 0))
    source_right = source_x + source_cols
    source_bottom = source_y + source_rows

    best_id: int | None = None
    best_key: tuple[int, int, int] | None = None
    for candidate in panes:
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, int) or candidate_id == source_pane.get("id"):
            continue
        candidate_x = int(candidate.get("pane_x", 0))
        candidate_y = int(candidate.get("pane_y", 0))
        candidate_cols = int(candidate.get("pane_columns", 0))
        candidate_rows = int(candidate.get("pane_rows", 0))
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
    target_id = target_pane.get("id")
    if not isinstance(target_id, int):
        return None
    focused_pane = next((pane for pane in panes if pane.get("is_focused")), None)
    focused_id = focused_pane.get("id") if focused_pane is not None else None
    if not isinstance(focused_id, int):
        return None
    if focused_id == target_id:
        return []

    panes_by_id = {
        pane["id"]: pane
        for pane in panes
        if isinstance(pane.get("id"), int)
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
