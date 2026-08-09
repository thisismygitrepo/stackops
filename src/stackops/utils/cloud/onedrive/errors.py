from collections.abc import Callable

import typer


class OneDriveError(Exception):
    pass


def run_cli[Result](operation: Callable[[], Result]) -> Result:
    try:
        return operation()
    except OneDriveError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from None
