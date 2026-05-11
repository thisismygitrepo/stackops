import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import file_utils_app


def test_read_db_help_lists_url_option() -> None:
    result = CliRunner().invoke(file_utils_app.get_app(), ["read-db", "--help"])

    assert result.exit_code == 0
    assert "--url" in result.stdout
    assert "-u" in result.stdout


def test_read_db_passes_url_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, object]] = []

    def fake_impl(
        *,
        path: str | None,
        url: str | None,
        find: str | None,
        find_root: str | None,
        recursive: bool,
        backend: str,
        read_only: bool,
        theme: str | None,
        limit: int | None,
    ) -> None:
        captured.append(
            {
                "path": path,
                "url": url,
                "find": find,
                "find_root": find_root,
                "recursive": recursive,
                "backend": backend,
                "read_only": read_only,
                "theme": theme,
                "limit": limit,
            }
        )

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui.app", fake_impl)

    result = CliRunner().invoke(file_utils_app.get_app(), ["read-db", "--url", "postgres://postgres:1234@192.168.20.4:5432/binance"])

    assert result.exit_code == 0
    assert captured == [
        {
            "path": None,
            "url": "postgres://postgres:1234@192.168.20.4:5432/binance",
            "find": None,
            "find_root": None,
            "recursive": False,
            "backend": "harlequin",
            "read_only": True,
            "theme": None,
            "limit": None,
        }
    ]
