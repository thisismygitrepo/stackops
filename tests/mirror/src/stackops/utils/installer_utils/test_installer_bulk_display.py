from pathlib import Path

from stackops.utils.installer_utils.installer_bulk_display import read_log_tail


def test_read_log_tail_keeps_last_redraw_and_drops_terminal_noise(tmp_path: Path) -> None:
    log_path = tmp_path.joinpath("tool.log")
    log_path.write_bytes(
        "╭──── fake installer ────╮\n"
        "│ Installing tool        │\n"
        "╰────────────────────────╯\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "\x1b[32mDownloading tool 10%\x1b[0m\rDownloading tool 55%\rDownloading tool 100%\n"
        "warning: something\r\n"
        "\n"
        "✅ installed\n".encode("utf-8")
    )

    assert read_log_tail(log_path=log_path, line_count=5) == [
        "fake installer",
        "Installing tool",
        "Downloading tool 100%",
        "warning: something",
        "✅ installed",
    ]
    assert read_log_tail(log_path=log_path, line_count=1) == ["✅ installed"]


def test_read_log_tail_shows_progress_still_being_drawn(tmp_path: Path) -> None:
    log_path = tmp_path.joinpath("tool.log")
    log_path.write_bytes(b"Retrieving release\nDownloading 5%\rDownloading 40%\r")

    assert read_log_tail(log_path=log_path, line_count=1) == ["Downloading 40%"]
