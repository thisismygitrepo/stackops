import pytest
from typer.testing import CliRunner

import stackops.scripts.python.seek as seek_app


def test_seek_help_lists_max_files_option() -> None:
    result = CliRunner().invoke(seek_app.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "--max-files" in result.stdout
    assert "-m" in result.stdout
    assert result.stdout.index("--install-req") < result.stdout.index("--max-files")


def test_seek_passes_max_files_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_limits: list[int] = []

    def fake_seek(
        *,
        path: str,
        search_term: str,
        ast: bool,
        semantic: bool,
        max_files: int,
        extension: str | None,
        file: bool,
        dotfiles: bool,
        rga: bool,
        edit: bool,
        install_dependencies: bool,
    ) -> None:
        _ = path, search_term, ast, semantic, extension, file, dotfiles, rga, edit, install_dependencies
        captured_limits.append(max_files)

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_seek.seek_impl.seek", fake_seek)

    result = CliRunner().invoke(seek_app.get_app(), ["--semantic", "-m", "900"])

    assert result.exit_code == 0
    assert captured_limits == [900]


def test_seek_rejects_missing_explicit_path() -> None:
    result = CliRunner().invoke(seek_app.get_app(), ["missing-path-for-seek-tests", "needle"])

    assert result.exit_code != 0
    assert "Search path does not exist" in result.output
