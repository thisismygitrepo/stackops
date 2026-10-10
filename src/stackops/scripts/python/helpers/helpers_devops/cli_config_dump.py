from pathlib import Path
from typing import Annotated, Never

import typer

from stackops.utils.managed_files import ManagedFileKind

DUMP_HELP = "Dump a packaged example file and its schema."


def _fail(message: str) -> Never:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def dump_config(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which managed file to dump.")],
    data: Annotated[bool, typer.Option("--data", "-d", help="Dump the example data file. Defaults to data and schema when omitted.")] = False,
    schema: Annotated[bool, typer.Option("--schema", "-s", help="Dump the matching schema file. Defaults to data and schema when omitted.")] = False,
    default_path: Annotated[
        bool,
        typer.Option("--default-path", "-p", help="Write to the real user file path instead of ./.stackops/examples."),
    ] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing output files.")] = False,
) -> None:
    from stackops.utils.managed_files import get_managed_file_spec, managed_schema_path

    spec = get_managed_file_spec(which)
    data_output_path = spec.user_path if default_path else Path.cwd() / ".stackops" / "examples" / spec.user_path.name
    dump_data, dump_schema = (data, schema) if data or schema else (True, True)
    copies: list[tuple[Path, Path]] = []
    if dump_data:
        copies.append((spec.example_source_path, data_output_path))
    if dump_schema:
        copies.append((spec.schema_source_path, managed_schema_path(spec=spec, data_path=data_output_path)))

    non_file_paths = [str(output_path) for _, output_path in copies if output_path.exists() and not output_path.is_file()]
    if non_file_paths:
        _fail(f"""Output path exists but is not a file: {", ".join(non_file_paths)}""")
    existing_paths = [str(output_path) for _, output_path in copies if output_path.exists()]
    if existing_paths and not force:
        _fail(f"""Refusing to overwrite existing file(s): {", ".join(existing_paths)}. Pass --force/-f to overwrite.""")

    for source_path, output_path in copies:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    written_paths = ", ".join(str(output_path) for _, output_path in copies)
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Wrote {written_paths}")
