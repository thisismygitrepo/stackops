from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer


DatabaseBackend: TypeAlias = Literal["rainfrog", "r", "lazysql", "l", "dblab", "d", "usql", "u", "harlequin", "h", "sqlit", "s"]
SuryaTask: TypeAlias = Literal["ocr", "detect", "layout", "table"]
SURYA_CONTEXT_SETTINGS = {"allow_extra_args": True, "ignore_unknown_options": True}
SCRAPE_CONTEXT_SETTINGS = {"allow_extra_args": True, "ignore_unknown_options": True}


def edit_file_with_hx(
    path: Annotated[str | None, typer.Argument(..., help="The root directory of the project to edit, or a file path.")] = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.python import edit_file_with_hx as impl

    impl(path=path)


def download(
    url: Annotated[str | None, typer.Argument(..., help="The URL to download the file from.")] = None,
    decompress: Annotated[bool, typer.Option(..., "--decompress", "-d", help="Decompress the file if it's an archive.")] = False,
    output: Annotated[str | None, typer.Option("--output", "-o", help="The output file path.")] = None,
    output_dir: Annotated[str | None, typer.Option("--output-dir", "-O", help="Directory to place the downloaded file in.")] = None,
) -> None:
    from stackops.utils.files.download import download as impl

    impl(url=url, decompress=decompress, output=output, output_dir=output_dir)


def scrape(
    url: Annotated[str | None, typer.Argument(..., help="The URL to scrape.")] = None,
    output_path: Annotated[str | None, typer.Argument(help="The output markdown file path. Defaults to f.md.")] = None,
    output: Annotated[str | None, typer.Option("--output", "-o", help="The output markdown file path.")] = None,
    selector: Annotated[str | None, typer.Option("--selector", "-s", help="CSS selector to extract.")] = "article",
    wait_selector: Annotated[str | None, typer.Option("--wait-selector", "-W", help="CSS selector to wait for before extracting.")] = "article",
    wait: Annotated[int | None, typer.Option("--wait", "-w", min=0, help="Milliseconds to wait after the page is ready.")] = 2000,
    timeout: Annotated[int | None, typer.Option("--timeout", "-t", min=1, help="Scrapling timeout in milliseconds.")] = 60000,
    enable_resources: Annotated[
        bool,
        typer.Option("--enable-resources/--no-enable-resources", "-e/-E", help="Enable browser resources while fetching."),
    ] = True,
    package_spec: Annotated[str, typer.Option("--package-spec", "-p", help="uvx package spec used to provide Scrapling.")] = "scrapling[shell]",
) -> None:
    if url is None:
        typer.echo("Error: URL is required.", err=True)
        raise typer.Exit(code=2)
    if output is not None and output_path is not None:
        raise typer.BadParameter("--output cannot be used with positional output_path.", param_hint="--output")
    if package_spec.strip() == "":
        raise typer.BadParameter("Package spec cannot be empty.", param_hint="--package-spec")
    if selector is not None and selector.strip() == "":
        raise typer.BadParameter("Selector cannot be empty.", param_hint="--selector")
    if wait_selector is not None and wait_selector.strip() == "":
        raise typer.BadParameter("Wait selector cannot be empty.", param_hint="--wait-selector")

    import click
    from stackops.scripts.python.helpers.helpers_utils.scrape import run_scrape as impl

    click_context = click.get_current_context(silent=True)
    returncode = impl(
        url=url,
        output_path=output or output_path or "f.md",
        selector=selector,
        wait_selector=wait_selector,
        wait=wait,
        timeout=timeout,
        enable_resources=enable_resources,
        package_spec=package_spec.strip(),
        extra_args=list(click_context.args) if click_context is not None else [],
    )
    if returncode != 0:
        raise typer.Exit(code=returncode)


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
        typer.Option("--skip-table-detection", "-S", help="For table recognition, treat the input as an already-cropped table."),
    ] = False,
    package_spec: Annotated[str, typer.Option("--package-spec", "-P", help="uv package spec used to provide Surya.")] = "surya-ocr",
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
        typer.Option("--find-root", "-R", help="Root directory for --find."),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option("--recursive", "-r", help="Search subdirectories when using --find."),
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
    file_app.command(name="scrape", no_args_is_help=True, help="<s> Scrape a page to Markdown with Scrapling.", context_settings=SCRAPE_CONTEXT_SETTINGS)(scrape)
    file_app.command(name="s", no_args_is_help=True, hidden=True, context_settings=SCRAPE_CONTEXT_SETTINGS)(scrape)
    file_app.command(name="pdf-merge", no_args_is_help=True, help="◫ <p> Merge PDF files into one.")(merge_pdfs)
    file_app.command(name="p", no_args_is_help=True, hidden=True)(merge_pdfs)
    file_app.command(name="pdf-compress", no_args_is_help=True, help="↧ <c> Compress a PDF file.")(compress_pdf)
    file_app.command(name="c", no_args_is_help=True, hidden=True)(compress_pdf)
    file_app.command(name="ocr", no_args_is_help=True, help="☀ <o> OCR, layout, detection, and table recognition with Surya.", context_settings=SURYA_CONTEXT_SETTINGS)(surya)
    file_app.command(name="o", no_args_is_help=True, hidden=True, context_settings=SURYA_CONTEXT_SETTINGS)(surya)
    file_app.command(name="read-db", no_args_is_help=False, help="🗃 <r> TUI DB Visualizer.")(read_db_cli_tui)
    file_app.command(name="r", no_args_is_help=False, hidden=True)(read_db_cli_tui)
    return file_app
