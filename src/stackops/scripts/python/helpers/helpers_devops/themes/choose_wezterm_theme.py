"""
Choose a theme for Wezterm
"""

from stackops.utils.options_utils.options import choose_from_options
from pathlib import Path
import json
import os
import re
from typing import TYPE_CHECKING
from rich.panel import Panel
from rich.console import Console
if TYPE_CHECKING:
    import curses

console = Console()


schemes_list = [
    "Pro",
    "Spiderman",
    "shades-of-purple",
    "synthwave",
    "Symfonic",
    "PaulMillr",
    "Neon",
    "LiquidCarbonTransparentInverse",
    "Laser",
    "IR_Black",
    "Hurtado",
    "Homebrew",
    "Hipster Green",
    "Firefly Traditional",
    "Elementary",
    "deep",
    "Dark Pastel",
    "Bright Lights",
    "Adventure",
    "Nancy (terminal.sexy)",
    "Bim (Gogh)",
    "BlueDolphin",
    "Borland",
    "Grass (Gogh)",
    "Greenscreen (light) (terminal.sexy)",
    "Grayscale (dark) (terminal.sexy)",
]


def main2() -> None:
    from stackops.utils.cli_utils.interaction import require_interactive

    require_interactive("WezTerm theme preview; supply --theme NAME")
    console.print(Panel("🎨 WezTerm Theme Selector", title_align="left", border_style="green"))
    option = choose_from_options(multi=False, options=schemes_list, header="Choose a theme for Wezterm", tv=True, msg="Use arrow keys to navigate, Enter to select a theme")
    if option is None:
        console.print(Panel("❓ Theme selection cancelled.", title_align="left", border_style="yellow"))
        return
    set_theme(option)
    print(f"✅ Theme set to: {option}")


def set_theme(theme: str) -> Path:
    if theme not in schemes_list:
        raise ValueError(f"Unknown WezTerm theme: {theme}")
    path = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "wezterm" / "wezterm.lua"
    txt_lines = path.read_text(encoding="utf-8").splitlines()
    res_lines: list[str] = []
    replaced = False
    for line in txt_lines:
        if re.match(r"^\s*config\.color_scheme\s*=", line):
            res_lines.append(f"config.color_scheme = {json.dumps(theme, ensure_ascii=False)}")
            replaced = True
        else:
            res_lines.append(line)
    if not replaced:
        raise ValueError(f"No config.color_scheme assignment found in {path}")
    path.write_text("\n".join(res_lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    import curses
    from stackops.utils.cli_utils.interaction import require_interactive

    require_interactive("WezTerm theme preview; supply --theme NAME")
    console.print(Panel("🎨 WezTerm Theme Selector - Interactive Mode", title_align="left", border_style="blue"))
    print("""
📝 Use arrow keys to navigate, Enter to select a theme
""")
    curses.wrapper(accessory)
    console.print(Panel("✅ Theme selection completed", title_align="left", border_style="green"))


def accessory(stdscr: "curses.window") -> None:
    import curses
    options = schemes_list
    current_option = 0
    page_size = stdscr.getmaxyx()[0] - 1  # curses.LINES - 1  # Number of lines in the terminal, -1 for status line

    while True:
        stdscr.clear()

        # Calculate start and end indices for options
        start_index = (current_option // page_size) * page_size
        end_index = start_index + page_size

        # Display options
        for i, option in enumerate(options[start_index:end_index]):
            if start_index + i == current_option:
                stdscr.addstr(i, 0, f"➤ {option}", curses.A_REVERSE)  # Highlighted with arrow
            else:
                stdscr.addstr(i, 0, f"  {option}")

        # Display status line
        status_line = f"🔍 Theme {current_option + 1}/{len(options)} | ↑/↓: Navigate | Enter: Select"
        stdscr.addstr(page_size, 0, status_line)

        # Get key press
        key = stdscr.getch()

        # Handle key press
        if key == curses.KEY_UP and current_option > 0:
            current_option -= 1
        elif key == curses.KEY_DOWN and current_option < len(options) - 1:
            current_option += 1
        elif key == ord("\n"):  # Enter key
            break  # Exit the loop
        set_theme(options[current_option])
