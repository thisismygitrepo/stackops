import pytest
from typer.testing import CliRunner

import stackops.scripts.python.seek as seek_app


def test_seek_help_lists_symantic_max_files_option() -> None:
    result = CliRunner().invoke(seek_app.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "--symantic-max-files" in result.stdout
    assert "Use 0 to disable the limit." in result.stdout


def test_seek_passes_symantic_max_files_to_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_limits: list[int] = []

    def fake_seek(
        *,
        path: str,
        search_term: str,
        ast: bool,
        symantic: bool,
        symantic_max_files: int,
        extension: str | None,
        file: bool,
        dotfiles: bool,
        rga: bool,
        edit: bool,
        install_dependencies: bool,
    ) -> None:
        _ = path, search_term, ast, symantic, extension, file, dotfiles, rga, edit, install_dependencies
        captured_limits.append(symantic_max_files)

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_seek.seek_impl.seek", fake_seek)

    result = CliRunner().invoke(seek_app.get_app(), ["--symantic", "--symantic-max-files", "900"])

    assert result.exit_code == 0
    assert captured_limits == [900]
