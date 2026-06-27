import glob
import os
import platform
import random
from pathlib import Path

from rich import box, pretty
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.utils.source_of_truth import WINDOWS_INSTALL_PATH


def print_header() -> None:
    console = Console()
    pretty.install()
    console.print(_build_header_panel())


def _build_header_panel() -> Panel:
    from stackops.version import get_stackops_version

    title = Text.assemble(
        ("StackOps Shell", "bold white"),
        (" "),
        (get_stackops_version(), "bold cyan"),
    )

    return Panel(
        _build_environment_table(),
        title=title,
        title_align="left",
        subtitle=Text("Built with love", style="dim"),
        subtitle_align="right",
        border_style="cyan",
        box=box.ROUNDED,
        expand=False,
        padding=(0, 1),
    )


def _build_environment_table() -> Table:
    table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    table.add_column("Label", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("Python", platform.python_version())
    table.add_row("System", platform.system())
    table.add_row("Environment", _virtual_environment())
    table.add_row("Directory", _display_path(Path.cwd()))
    return table


def _virtual_environment() -> str:
    virtual_environment = os.getenv("VIRTUAL_ENV")
    if virtual_environment is None or virtual_environment == "":
        return "not active"
    return _display_path(Path(virtual_environment))


def _display_path(path: Path) -> str:
    home = Path.home()
    if path == home:
        return "~"
    if path.is_relative_to(home):
        return f"~/{path.relative_to(home).as_posix()}"
    return path.as_posix()


def print_logo(logo: str) -> None:
    from stackops.utils.files.ascii_art import font_box_color, character_color, character_or_box_color
    if platform.system() == "Windows":
        _1x = Path.home().joinpath(r"AppData/Roaming/npm/figlet").exists()
        _2x = Path.home().joinpath(r"AppData/Roaming/npm/lolcatjs").exists()
        _3x = Path(WINDOWS_INSTALL_PATH).joinpath("boxes.exe").exists()
        if _1x and _2x and _3x:
            if random.choice([True, True, False]): font_box_color(logo)
            else: character_color(logo)
        else:
            # print("\n" + "🚫 " + "-" * 70 + " 🚫")
            # print("🔍 Missing ASCII art dependencies. Install with: iwr bit.ly/cfgasciiartwindows | iex")
            # print("🚫 " + "-" * 70 + " 🚫\n")
            _default_art = Path(random.choice([item for item in glob.glob(str(Path(__file__).parent.joinpath("art", "*"))) if Path(item).is_file() and item.endswith(".txt")]))
            print(_default_art.read_text())
    elif platform.system() in ["Linux", "Darwin"]:  # Explicitly handle both Linux and macOS
        from stackops.utils.cli_utils.command_lookup import is_executable_in_path
        avail_cowsay = is_executable_in_path("cowsay")
        avail_lolcat = is_executable_in_path("lolcatjs")
        avail_boxes = is_executable_in_path("boxes")
        avail_figlet = is_executable_in_path("figlet")
        if avail_cowsay and avail_lolcat and avail_boxes and avail_figlet:
            # _dynamic_art = random.choice([True, True, True, True, False])
            # if _dynamic_art: character_or_box_color(logo=logo)
            # else:
            #     print(Path(random.choice(glob.glob(str(Path(__file__).parent.joinpath("art", "*"))))).read_text())
            character_or_box_color(logo=logo)
        else:
            from stackops.utils.schemas.installer.package_groups import PACKAGE_NAME
            pacakage_name: PACKAGE_NAME = "eye"
            install_cmd = f"d install --group {pacakage_name}"
            print(f"🔍 Missing ASCII art dependencies. Install with: {install_cmd}  | {avail_boxes=} {avail_cowsay} {avail_figlet} {avail_lolcat=}")
            _default_art = Path(random.choice(glob.glob(str(Path(__file__).parent.joinpath("art", "*")))))
            print(_default_art.read_text())
    else:
        print(f"⚠️ Platform {platform.system()} not supported for ASCII art. Using default art.")
        _default_art = Path(random.choice(glob.glob(str(Path(__file__).parent.joinpath("art", "*")))))
        print(_default_art.read_text())
