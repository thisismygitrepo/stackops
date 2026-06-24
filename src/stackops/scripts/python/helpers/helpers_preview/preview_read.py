
from collections.abc import Mapping, Sequence
from itertools import islice
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def _format_mapping_preview(dat: Mapping[object, object]) -> str:
    shown_keys = list(islice(dat.keys(), 20))
    keys_line = ", ".join(str(key)[:120] for key in shown_keys)
    hidden_count = len(dat) - len(shown_keys)
    if hidden_count > 0:
        keys_line = f"{keys_line}, ... ({hidden_count} more)"
    return f"Mapping preview suppressed\nType: {type(dat).__name__}\nItems: {len(dat)}\nKeys: {keys_line}"


def _is_json_like_sequence(dat: Sequence[object]) -> bool:
    return any(isinstance(item, Mapping | list | tuple) for item in dat[:20])


def _format_sequence_preview(dat: Sequence[object]) -> str:
    return f"Sequence preview suppressed\nType: {type(dat).__name__}\nItems: {len(dat)}"


def print_data_preview(console: Console, path: Path, dat: object) -> None:
    if isinstance(dat, Mapping):
        text = _format_mapping_preview(dat=dat)
    elif isinstance(dat, Sequence) and not isinstance(dat, str | bytes | bytearray) and _is_json_like_sequence(dat=dat):
        text = _format_sequence_preview(dat=dat)
    else:
        text = str(dat)
    panel_title = f"📄 Successfully read the file: {path.name}"
    console.print(Panel(Text(text, justify="left"), title=panel_title, expand=False))


def get_read_python_file_pycode(path: str, title: str) -> None:
    from pathlib import Path
    print("Reading code from path:", path)
    pycode = Path(path).read_text(encoding="utf-8")
    pycode = pycode.split("except Exception: print(pycode)")[2]
    try:
        # from rich.text import Text
        from rich.panel import Panel
        from rich.console import Console
        from rich.syntax import Syntax
        console = Console()
        if pycode.strip() != "":
            console.print(Panel(Syntax(pycode, lexer="python"), title=title), style="bold red")
    except Exception: print(pycode)


def get_read_data_pycode(path: str) -> None:
    console = Console()
    p = Path(path).absolute()
    try:
        from stackops.utils.files.read import read_file
        dat = read_file(p)
        print_data_preview(console=console, path=p, dat=dat)
    except Exception as e:
        error_message = f'''❌ ERROR READING FILE\nFile: {p.name}\nError: {e}'''
        console.print(Panel(Text(error_message, justify="left"), title="Error", expand=False, border_style="red"))
