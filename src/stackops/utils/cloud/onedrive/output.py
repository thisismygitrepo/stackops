import json
import sys
from collections.abc import Iterable, Sequence

import typer


type TableRow = Sequence[object]


def json_output(payload: object) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    typer.echo()


def print_table(headers: Sequence[str], rows: Iterable[TableRow]) -> None:
    rendered: list[list[str]] = []
    for row in rows:
        rendered.append(["" if value is None else str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ") for value in row])

    widths = [len(header) for header in headers]
    for row in rendered:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    typer.echo("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    for row in rendered:
        typer.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
