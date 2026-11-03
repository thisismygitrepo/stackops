import typer

from stackops.secrets.models import Login


def select_subset_indices(*, entries: list[Login], names: list[str], entry_indices: list[int], all_matches: bool) -> list[int]:
    invalid_indices = [index for index in entry_indices if index < 0 or index >= len(entries)]
    if invalid_indices:
        raise typer.BadParameter(f"Entry indices outside entries[]: {invalid_indices}")
    if all_matches and entry_indices:
        raise typer.BadParameter("--all-matches cannot be combined with --entry-index.")
    selected = set(entry_indices)
    if all_matches and not names:
        return list(range(len(entries)))
    for name in names:
        matches = [index for index, entry in enumerate(entries) if entry["name"] == name]
        if not matches:
            raise typer.BadParameter(f"No login has the exact name {name!r}.")
        if len(matches) > 1 and not all_matches:
            raise typer.BadParameter(f"Login name {name!r} is ambiguous at indices {matches}; use --entry-index or --all-matches.")
        selected.update(matches)
    return sorted(selected)
