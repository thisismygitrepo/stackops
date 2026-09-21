"""ftpx - File transfer utility through SSH."""

import typer
from typing import Annotated
from typer._completion_classes import completion_init
from typer.completion import install_callback, show_callback


def _is_remote_path(path: str) -> bool:
    return ":" in path and (path[1] != ":" if len(path) > 1 else True)


def _run_ftpx_impl(source: str, target: str, recursive: bool, zip_first: bool, cloud: bool, overwrite_existing: bool) -> None:
    from stackops.scripts.python.helpers.helpers_network.ftpx_impl import ftpx as impl

    try:
        impl(source=source, target=target, recursive=recursive, zip_first=zip_first, cloud=cloud, overwrite_existing=overwrite_existing)
    except ValueError as err:
        import sys

        print(str(err), file=sys.stderr)
        sys.exit(2)
    except (OSError, RuntimeError) as err:
        import sys

        message = str(err).strip()
        if message.startswith("SSH Error: "):
            message = message.removeprefix("SSH Error: ").strip()
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(1)


def ftpx(
    source: Annotated[str, typer.Argument(help="Source path (machine:path)")],
    target: Annotated[str, typer.Argument(help="Target path (machine:path)")],
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Send recursively.")] = False,
    zip_first: Annotated[bool, typer.Option("--zip-first", "-z", help="Zip before sending.")] = False,
    cloud: Annotated[bool, typer.Option("--cloud", "-c", help="Transfer through the cloud.")] = False,
    overwrite_existing: Annotated[bool, typer.Option("--overwrite-existing", "-o", help="Overwrite existing files on remote when sending from local to remote.")] = False,
    _install_completion: Annotated[
        bool, typer.Option("--install-completion", "-I", callback=install_callback, expose_value=False, help="Install completion for the current shell.")
    ] = False,
    _show_completion: Annotated[
        bool, typer.Option("--show-completion", "-S", callback=show_callback, expose_value=False, help="Show completion for the current shell, to copy it or customize the installation.")
    ] = False,
) -> None:
    """File transfer utility through SSH."""
    if not _is_remote_path(source) and not _is_remote_path(target):
        _run_ftpx_impl(source=source, target=target, recursive=recursive, zip_first=zip_first, cloud=cloud, overwrite_existing=overwrite_existing)
        return

    from stackops.utils.code import run_lambda_function
    from stackops.utils.optional_dependencies import PARAMIKO_UV_WITH

    proc = run_lambda_function(
        lambda: _run_ftpx_impl(
            source=source,
            target=target,
            recursive=recursive,
            zip_first=zip_first,
            cloud=cloud,
            overwrite_existing=overwrite_existing,
        ),
        uv_with=list(PARAMIKO_UV_WITH),
        uv_project_dir=None,
    )
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


def main() -> None:
    """Entry point function that uses typer to parse arguments and call main."""
    completion_init()
    app = typer.Typer(add_completion=False, context_settings={"help_option_names": ["-h", "--help"]})
    app.command(no_args_is_help=True, help=ftpx.__doc__, short_help="File transfer utility through SSH.")(ftpx)
    app()


if __name__ == "__main__":
    main()
