from pathlib import Path

from stackops.settings.yazi.scripts import interactive_view


def test_database_mode_uses_selected_sql_backend(tmp_path: Path) -> None:
    target_path = tmp_path.joinpath("data.sqlite")
    target_path.write_text("", encoding="utf-8")

    assert interactive_view.build_command(
        target_path=target_path,
        mode="database",
        database_backend="rainfrog",
    ) == [
        "rainfrog",
        "--url",
        f"sqlite://{target_path.resolve().as_uri().removeprefix('file://')}?mode=ro",
    ]

