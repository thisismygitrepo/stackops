import csv
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.table import Table


def parse_apps_argument(apps: str | None) -> list[str] | None:
    if apps is None:
        return None
    app_names = [name.strip() for name in apps.split(",") if name.strip()]
    if not app_names:
        raise ValueError("Supply at least one app name.")
    return app_names


def render_csv_text(rows: Sequence[Mapping[str, object]], columns: Sequence[str]) -> str:
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(columns))
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column) for column in columns})
    return buffer.getvalue().rstrip("\r\n")


def build_raw_csv_table(title: str, rows: Sequence[Mapping[str, object]], columns: Sequence[str]) -> "Table":
    from rich import box
    from rich.table import Table
    from rich.text import Text

    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan", row_styles=["", "dim"], expand=False)
    for column in columns:
        table.add_column(column.replace("_", " "), overflow="fold", max_width=44)
    for row in rows:
        table.add_row(*[Text("" if row.get(column) is None else str(row[column])) for column in columns])
    return table
