from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer


DatabaseBackend: TypeAlias = Literal["rainfrog", "r", "lazysql", "l", "dblab", "d", "usql", "u", "harlequin", "h", "sqlit", "s"]
SuryaTask: TypeAlias = Literal["ocr", "detect", "layout", "table"]
SURYA_CONTEXT_SETTINGS = {"allow_extra_args": True, "ignore_unknown_options": True}


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

    # Resolve and validate input paths strictly
    input_paths = [Path(pdf_path).expanduser().resolve() for pdf_path in pdfs]

    # Detect duplicate inputs after resolution
    seen: set[Path] = set()
    duplicates: list[str] = []
    unique_input_paths: list[Path] = []
    for p in input_paths:
        if p in seen:
            duplicates.append(str(p))
        else:
            seen.add(p)
            unique_input_paths.append(p)

    if duplicates:
        raise typer.BadParameter(
            f"Duplicate input PDF paths detected (after resolution): {', '.join(duplicates)}",
            param_hint="pdfs",
        )

    if len(unique_input_paths) < 2:
        raise typer.BadParameter("Provide at least two distinct PDF files to merge.", param_hint="pdfs")

    # Ensure inputs exist and are regular files
    missing = [str(p) for p in unique_input_paths if not p.exists()]
    not_files = [str(p) for p in unique_input_paths if p.exists() and not p.is_file()]
    if missing:
        raise typer.BadParameter(f"Input PDF files not found: {', '.join(missing)}", param_hint="pdfs")
    if not_files:
        raise typer.BadParameter(f"Input paths are not regular files: {', '.join(not_files)}", param_hint="pdfs")

    output_path = Path(output if output is not None else "merged.pdf").expanduser().resolve()

    # Prevent writing output over any input file
    if output_path in unique_input_paths:
        raise typer.BadParameter("Output PDF path must not be one of the input PDF paths.", param_hint="--output")

    # Fail if output already exists to avoid accidental overwrite
    if output_path.exists():
        raise typer.BadParameter(
            f"Output path already exists: {output_path}. Remove it or choose a different --output.",
            param_hint="--output",
        )

    output_parent = output_path.parent
    if not output_parent.exists():
        raise typer.BadParameter(
            f"Output directory does not exist: {output_parent}",
            param_hint="--output",
        )
    if not output_parent.is_dir():
        raise typer.BadParameter(
            f"Output parent path is not a directory: {output_parent}",
            param_hint="--output",
        )

    from stackops.scripts.python.helpers.helpers_utils.pdf import merge_pdfs as impl

    # Call implementation with resolved paths (strings) for consistency
    impl(pdfs=[str(p) for p in unique_input_paths], output=str(output_path), compress=compress)


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
        typer.Option("--no-compress-streams", "-C", help="Do not compress uncompressed streams."),
    ] = True,
    use_objstms: Annotated[
        bool,
        typer.Option("--no-object-streams", "-S", help="Do not use object streams for additional compression."),
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


def surya(
    data_path: Annotated[str, typer.Argument(..., help="Path to an image, PDF, or folder for Surya.")],
    task: Annotated[SuryaTask, typer.Option("--task", "-t", help="Surya task to run.")] = "ocr",
    output_dir: Annotated[str | None, typer.Option("--output-dir", "-o", help="Directory for Surya results.")] = None,
    page_range: Annotated[str | None, typer.Option("--page-range", "-p", help="PDF page range, for example: 0,5-10,20.")] = None,
    images: Annotated[bool, typer.Option("--images", "-i", help="Save annotated page images where Surya supports it.")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d", help="Enable Surya debug output.")] = False,
    keep_server: Annotated[bool, typer.Option("--keep-server", "-k", help="Leave Surya's inference server running for later commands.")] = False,
    skip_table_detection: Annotated[
        bool,
        typer.Option("--skip-table-detection", help="For table recognition, treat the input as an already-cropped table."),
    ] = False,
    package_spec: Annotated[str, typer.Option("--package-spec", help="uv package spec used to provide Surya.")] = "surya-ocr",
) -> None:
    if not package_spec.strip():
        raise typer.BadParameter("Package spec cannot be empty.", param_hint="--package-spec")

    if skip_table_detection and task != "table":
        raise typer.BadParameter("--skip-table-detection is only valid with --task table.", param_hint="--skip-table-detection")

    input_path = Path(data_path).expanduser().resolve()
    if not input_path.exists():
        raise typer.BadParameter(f"Input path not found: {input_path}", param_hint="data_path")
    if not (input_path.is_file() or input_path.is_dir()):
        raise typer.BadParameter(f"Input path is not a file or directory: {input_path}", param_hint="data_path")

    output_dir_path: str | None = None
    if output_dir is not None:
        resolved_output_dir = Path(output_dir).expanduser().resolve()
        if resolved_output_dir.exists() and not resolved_output_dir.is_dir():
            raise typer.BadParameter(f"Output path is not a directory: {resolved_output_dir}", param_hint="--output-dir")
        output_dir_path = str(resolved_output_dir)

    import click
    from stackops.scripts.python.helpers.helpers_utils.surya import run_surya as impl

    click_context = click.get_current_context(silent=True)

    returncode = impl(
        data_path=str(input_path),
        task=task,
        output_dir=output_dir_path,
        page_range=page_range,
        images=images,
        debug=debug,
        keep_server=keep_server,
        skip_table_detection=skip_table_detection,
        package_spec=package_spec,
        extra_args=list(click_context.args) if click_context is not None else [],
    )
    if returncode != 0:
        raise typer.Exit(code=returncode)


def read_db_cli_tui(
    path: Annotated[str | None, typer.Argument(..., help="The path to the file-based db")] = None,
    url: Annotated[
        str | None,
        typer.Option("--url", "-u", help="Database connection URL. Use this instead of the positional path for DSNs."),
    ] = None,
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
        typer.Option("--read-write", "-w", help="Open the database in read/write mode (if supported by backend)."),
    ] = True,
    theme: Annotated[str | None, typer.Option("--theme", "-t", help="Theme to use (if supported by backend).")] = None,
    limit: Annotated[int | None, typer.Option("--limit", "-l", help="Maximum number of rows to load (if supported by backend).")] = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui import app as impl

    impl(
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


def get_app() -> typer.Typer:
    file_app = typer.Typer(help="📁 <f> File, document, and database utilities", no_args_is_help=True, add_help_option=True, add_completion=False)
    file_app.command(name="edit", no_args_is_help=False, help="✏ <e> Open a file in the default editor.")(edit_file_with_hx)
    file_app.command(name="e", no_args_is_help=False, hidden=True)(edit_file_with_hx)
    file_app.command(name="download", no_args_is_help=True, help="↓ <d> Download a file from a URL and optionally decompress it.")(download)
    file_app.command(name="d", no_args_is_help=True, hidden=True)(download)
    file_app.command(name="pdf-merge", no_args_is_help=True, help="◫ <p> Merge PDF files into one.")(merge_pdfs)
    file_app.command(name="p", no_args_is_help=True, hidden=True)(merge_pdfs)
    file_app.command(name="pdf-compress", no_args_is_help=True, help="↧ <c> Compress a PDF file.")(compress_pdf)
    file_app.command(name="c", no_args_is_help=True, hidden=True)(compress_pdf)
    file_app.command(name="surya", no_args_is_help=True, help="☀ <s> OCR, layout, detection, and table recognition with Surya.", context_settings=SURYA_CONTEXT_SETTINGS)(surya)
    file_app.command(name="s", no_args_is_help=True, hidden=True, context_settings=SURYA_CONTEXT_SETTINGS)(surya)
    file_app.command(name="read-db", no_args_is_help=False, help="🗃 <r> TUI DB Visualizer.")(read_db_cli_tui)
    file_app.command(name="r", no_args_is_help=False, hidden=True)(read_db_cli_tui)
    return file_app
