from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer


DatabaseBackend: TypeAlias = Literal["rainfrog", "r", "lazysql", "l", "dblab", "d", "usql", "u", "harlequin", "h", "sqlit", "s"]


def edit_file_with_hx(
    path: Annotated[str | None, typer.Argument(..., help="The root directory of the project to edit, or a file path.")] = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.python import edit_file_with_hx as impl

    impl(path=path)


def download(
    url: Annotated[str | None, typer.Argument(..., help="The URL to download the file from.")] = None,
    decompress: Annotated[bool, typer.Option(..., "--decompress", "-d", help="Decompress the file if it's an archive.")] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="The output file path.")] = None,
    output_dir: Annotated[str | None, typer.Option("--output-dir", help="Directory to place the downloaded file in.")] = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.download import download as impl

    impl(url=url, decompress=decompress, output=output, output_dir=output_dir)


def merge_pdfs(
    pdfs: Annotated[list[str], typer.Argument(..., help="Paths to at least two PDF files to merge.")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output merged PDF file path.")] = None,
    compress: Annotated[bool, typer.Option("--compress", "-c", help="Compress the output PDF.")] = False,
) -> None:
    if len(pdfs) < 2:
        raise typer.BadParameter("Provide at least two PDF files to merge.", param_hint="pdfs")

    output_path = Path(output if output is not None else "merged.pdf").expanduser().resolve()
    input_paths = [Path(pdf_path).expanduser().resolve() for pdf_path in pdfs]
    if output_path in input_paths:
        raise typer.BadParameter("Output PDF path must not be one of the input PDF paths.", param_hint="--output")

    from stackops.scripts.python.helpers.helpers_utils.pdf import merge_pdfs as impl

    impl(pdfs=pdfs, output=output, compress=compress)


def compress_pdf(
    pdf_input: Annotated[str, typer.Argument(..., help="Path to the input PDF file to compress.")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output compressed PDF file path.")] = None,
    quality: Annotated[
        int,
        typer.Option("--quality", "-q", min=0, max=100, help="JPEG quality for image compression (0-100, 0=no change, 100=best)."),
    ] = 85,
    image_dpi: Annotated[
        int,
        typer.Option("--image-dpi", "-d", min=0, help="Target DPI for image resampling (0=no resampling)."),
    ] = 0,
    compress_streams: Annotated[
        bool,
        typer.Option("--compress-streams/--no-compress-streams", "-c/-C", help="Compress uncompressed streams."),
    ] = True,
    use_objstms: Annotated[
        bool,
        typer.Option("--object-streams/--no-object-streams", "-s/-S", help="Use object streams for additional compression."),
    ] = True,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.pdf import compress_pdf as impl

    impl(
        pdf_input=pdf_input,
        output=output,
        quality=quality,
        image_dpi=image_dpi,
        compress_streams=compress_streams,
        use_objstms=use_objstms,
    )


def read_db_cli_tui(
    path: Annotated[str | None, typer.Argument(..., help="The path to the file-based db")] = None,
    find: Annotated[
        str | None,
        typer.Option("--find", "-f", help="Glob pattern to discover database files."),
    ] = None,
    find_root: Annotated[
        str | None,
        typer.Option("--find-root", help="Root directory for --find."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", help="Search subdirectories when using --find."),
    ] = False,
    backend: Annotated[DatabaseBackend, typer.Option("--backend", "-b", help="The TUI database client to use.")] = "harlequin",
    read_only: Annotated[
        bool,
        typer.Option("--read-only/--read-write", "-r/-w", help="Open the database in read-only mode (if supported by backend)."),
    ] = True,
    theme: Annotated[str | None, typer.Option("--theme", "-t", help="Theme to use (if supported by backend).")] = None,
    limit: Annotated[int | None, typer.Option("--limit", "-l", help="Maximum number of rows to load (if supported by backend).")] = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui import app as impl

    impl(
        path=path,
        find=find,
        find_root=find_root,
        recursive=recursive,
        backend=backend,
        read_only=read_only,
        theme=theme,
        limit=limit,
    )


def get_app() -> typer.Typer:
    file_app = typer.Typer(help="📁 <f> File, document, and database utilities", no_args_is_help=True, add_help_option=True, add_completion=False)
    file_app.command(name="edit", no_args_is_help=False, help="✏ <e> Open a file in the default editor.")(edit_file_with_hx)
    file_app.command(name="e", no_args_is_help=False, hidden=True)(edit_file_with_hx)
    file_app.command(name="download", no_args_is_help=True, help="↓ <d> Download a file from a URL and optionally decompress it.")(download)
    file_app.command(name="d", no_args_is_help=True, hidden=True)(download)
    file_app.command(name="pdf-merge", no_args_is_help=True, help="◫ <p> Merge PDF files into one.")(merge_pdfs)
    file_app.command(name="p", no_args_is_help=True, hidden=True)(merge_pdfs)
    file_app.command(name="pm", no_args_is_help=True, hidden=True)(merge_pdfs)
    file_app.command(name="pdf-compress", no_args_is_help=True, help="↧ <c> Compress a PDF file.")(compress_pdf)
    file_app.command(name="c", no_args_is_help=True, hidden=True)(compress_pdf)
    file_app.command(name="pc", no_args_is_help=True, hidden=True)(compress_pdf)
    file_app.command(name="read-db", no_args_is_help=False, help="🗃 <r> TUI DB Visualizer.")(read_db_cli_tui)
    file_app.command(name="r", no_args_is_help=False, hidden=True)(read_db_cli_tui)
    file_app.command(name="db", no_args_is_help=False, hidden=True)(read_db_cli_tui)
    return file_app
