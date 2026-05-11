import pytest
import typer

from stackops.scripts.python.helpers.helpers_utils import read_db_cli_tui
from stackops.scripts.python.helpers.helpers_utils import read_db_cli_tui_backend


def test_positional_path_rejects_database_urls() -> None:
    with pytest.raises(ValueError, match="--url"):
        read_db_cli_tui.app(path="postgres://postgres:1234@192.168.20.4:5432/binance")


def test_harlequin_postgres_url_uses_adapter_and_preserves_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_commands: list[list[str]] = []

    def fake_launch(command: list[str]) -> None:
        captured_commands.append(command)

    monkeypatch.setattr(read_db_cli_tui_backend, "_harlequin_installed_adapters", lambda: frozenset({"duckdb", "sqlite", "postgres"}))
    monkeypatch.setattr(read_db_cli_tui_backend, "_launch_interactive_command", fake_launch)

    read_db_cli_tui.app(
        url="postgres://postgres:1234@192.168.20.4:5432/binance",
        theme="nord",
        limit=200,
    )

    assert captured_commands == [
        [
            "harlequin",
            "--adapter",
            "postgres",
            "--read-only",
            "--theme",
            "nord",
            "--limit",
            "200",
            "postgres://postgres:1234@192.168.20.4:5432/binance",
        ]
    ]


def test_harlequin_postgres_url_rejects_uninstalled_adapter(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def should_not_launch(_command: list[str]) -> None:
        raise AssertionError("harlequin should not be launched when the adapter is unavailable")

    monkeypatch.setattr(read_db_cli_tui_backend, "_harlequin_installed_adapters", lambda: frozenset({"duckdb", "sqlite"}))
    monkeypatch.setattr(read_db_cli_tui_backend, "_launch_interactive_command", should_not_launch)

    with pytest.raises(typer.BadParameter, match="Installed harlequin does not support the 'postgres' adapter"):
        read_db_cli_tui.app(url="postgres://postgres:1234@192.168.20.4:5432/binance")

    captured = capsys.readouterr()
    expected_command = read_db_cli_tui_backend._format_command(
        [
            "harlequin",
            "--adapter",
            "postgres",
            "--read-only",
            "postgres://postgres:1234@192.168.20.4:5432/binance",
        ]
    )
    assert f"Built command: {expected_command}" in captured.err


def test_failed_launch_still_prints_built_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_launch(command: list[str]) -> None:
        assert command == [
            "lazysql",
            "-read-only",
            "postgres://postgres:1234@192.168.20.4:5432/binance",
        ]
        raise typer.Exit(code=1)

    monkeypatch.setattr(read_db_cli_tui_backend, "_launch_interactive_command", fake_launch)

    with pytest.raises(typer.Exit) as exc_info:
        read_db_cli_tui.app(
            url="postgres://postgres:1234@192.168.20.4:5432/binance",
            backend="lazysql",
        )

    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    expected_command = read_db_cli_tui_backend._format_command(
        [
            "lazysql",
            "-read-only",
            "postgres://postgres:1234@192.168.20.4:5432/binance",
        ]
    )
    assert f"Built command: {expected_command}" in captured.err
