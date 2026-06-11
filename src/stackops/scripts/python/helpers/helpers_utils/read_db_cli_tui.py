from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stackops.utils.read_db_cli_tui_backend import BACKEND_LOOSE


def app(
    path: str | None = None,
    url: str | None = None,
    find: str | None = None,
    find_root: str | None = None,
    recursive: bool = False,
    backend: "BACKEND_LOOSE" = "harlequin",
    read_only: bool = True,
    theme: str | None = None,
    limit: int | None = None,
) -> None:
    """🗃️ TUI DB Visualizer.

    path       – explicit file path (single DB).
    find       – glob pattern to discover DB files, e.g. '*.duckdb' or '**/*.duckdb'.
    find_root  – root directory for `find` (default: current working directory).
    recursive  – search subdirectories when using `find`.
    """
    from stackops.utils.read_db_cli_tui_backend import run_read_db_cli_tui

    run_read_db_cli_tui(
        path=path,
        url=url,
        find=find,
        find_root=find_root,
        recursive=recursive,
        backend=backend,
        read_only=read_only,
        theme=theme,
        limit=limit,
    )
