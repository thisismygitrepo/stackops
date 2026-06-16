import ast
from pathlib import Path

from stackops.settings.yazi.scripts import interactive_view


YAZI_SCRIPT_DIR = Path("src/stackops/settings/yazi/scripts")
ISOLATED_SCRIPT_NAMES: tuple[str, ...] = (
    "interactive_view.py",
    "serve_browser_file.py",
)


def stackops_import_lines(path: Path) -> list[int]:
    parsed_module = ast.parse(path.read_text(encoding="utf-8"))
    lines: list[int] = []
    for node in ast.walk(parsed_module):
        match node:
            case ast.Import():
                for alias in node.names:
                    if alias.name == "stackops" or alias.name.startswith("stackops."):
                        lines.append(node.lineno)
            case ast.ImportFrom(module=str(module)):
                if module == "stackops" or module.startswith("stackops."):
                    lines.append(node.lineno)
    return lines


def test_isolated_yazi_scripts_do_not_import_stackops() -> None:
    for script_name in ISOLATED_SCRIPT_NAMES:
        script_path = YAZI_SCRIPT_DIR / script_name
        assert stackops_import_lines(path=script_path) == []


def test_interactive_database_command_builds_harlequin_duckdb(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.duckdb"
    database_path.write_bytes(b"")

    command = interactive_view.build_database_command(target_path=database_path)

    assert command == [
        "harlequin",
        "--adapter",
        "duckdb",
        "--read-only",
        str(database_path),
    ]


def test_interactive_database_command_builds_rainfrog_sqlite_readonly(tmp_path: Path) -> None:
    database_path = tmp_path / "bot.sqlite"
    database_path.write_bytes(b"")

    command = interactive_view.build_database_command(target_path=database_path, database_backend="rainfrog")

    assert command[0:2] == ["rainfrog", "--url"]
    assert command[2].startswith("sqlite://")
    assert command[2].endswith("?mode=ro")
