from unittest.mock import patch
from pathlib import Path
import textwrap

from machineconfig.scripts.python.helpers.helpers_seek import seek_impl
from machineconfig.scripts.python.helpers.helpers_search.ast_search import SymbolInfo


def test_seek_limits_default_file_source_to_non_dotfiles() -> None:
    with patch("platform.system", return_value="Linux"), patch("machineconfig.utils.code.run_shell_script") as run_shell_script:
        seek_impl.seek(
            path=".",
            search_term="",
            ast=False,
            symantic=False,
            extension="",
            file=True,
            dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert run_shell_script.call_count == 1
    script = run_shell_script.call_args.kwargs["script"]
    assert "fd --type file | " in script


def test_seek_keeps_default_file_source_when_dotfiles_enabled() -> None:
    with patch("platform.system", return_value="Linux"), patch("machineconfig.utils.code.run_shell_script") as run_shell_script:
        seek_impl.seek(
            path=".",
            search_term="",
            ast=False,
            symantic=False,
            extension="",
            file=True,
            dotfiles=True,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert run_shell_script.call_count == 1
    script = run_shell_script.call_args.kwargs["script"]
    assert not script.startswith("fd ")


def test_seek_windows_file_search_changes_directory_with_literal_path() -> None:
    with patch("platform.system", return_value="Windows"), patch("machineconfig.utils.code.run_shell_script") as run_shell_script:
        seek_impl.seek(
            path="C:/Users/Alex/My Repo",
            search_term="",
            ast=False,
            symantic=False,
            extension="",
            file=True,
            dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert run_shell_script.call_count == 1
    script = run_shell_script.call_args.kwargs["script"]
    assert script.startswith("Set-Location -LiteralPath 'C:/Users/Alex/My Repo'\n")


def test_seek_windows_text_search_changes_directory_with_literal_path() -> None:
    with patch("platform.system", return_value="Windows"), patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script:
        seek_impl.seek(
            path="C:/Users/Alex/My Repo",
            search_term="needle",
            ast=False,
            symantic=False,
            extension="",
            file=False,
            dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert exit_then_run_shell_script.call_count == 1
    script = exit_then_run_shell_script.call_args.kwargs["script"]
    assert script.startswith("Set-Location -LiteralPath 'C:/Users/Alex/My Repo'\n")
    assert "$initialQuery = 'needle'" in script


def test_seek_macos_text_search_script_does_not_exit_parent_shell() -> None:
    with patch("platform.system", return_value="Darwin"), patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script:
        seek_impl.seek(
            path="/Users/alex/My Repo",
            search_term="needle",
            ast=False,
            symantic=False,
            extension="",
            file=False,
            dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert exit_then_run_shell_script.call_count == 1
    script = exit_then_run_shell_script.call_args.kwargs["script"]
    assert script.startswith("cd '/Users/alex/My Repo'\n")
    assert "INITIAL_QUERY=needle" in script
    assert "\nexit 0" not in script


def test_search_file_with_context_quotes_preview_path_on_windows() -> None:
    with patch("platform.system", return_value="Windows"):
        code = seek_impl.search_file_with_context(path="/tmp/My File.txt", is_temp_file=False, edit=False)

    assert "--preview-command 'bat --color=always --style=numbers --highlight-line {split: :0} \"/tmp/My File.txt\"'" in code


def test_seek_ast_uses_tv_preview_with_symbol_body() -> None:
    symbol: SymbolInfo = {
        "type": "function",
        "name": "sample",
        "path": "demo.sample",
        "file_path": "demo.py",
        "line": 3,
        "end_line": 4,
        "docstring": "hello",
        "body": "def sample() -> None:\n    pass",
    }
    captured_preview_map: dict[str, str] = {}
    captured_extension: str | None = None
    captured_multi: bool | None = None
    captured_preview_size_percent: float | None = None

    def _fake_choose(*, options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> str | None:
        nonlocal captured_extension, captured_multi, captured_preview_size_percent
        captured_preview_map.update(options_to_preview_mapping)
        captured_extension = extension
        captured_multi = multi
        captured_preview_size_percent = preview_size_percent
        return next(iter(options_to_preview_mapping))

    with (
        patch("machineconfig.scripts.python.helpers.helpers_search.ast_search.get_repo_symbols", return_value=[symbol]),
        patch("machineconfig.utils.options_utils.tv_options.choose_from_dict_with_preview", side_effect=_fake_choose),
        patch("rich.print_json") as print_json,
    ):
        seek_impl.seek(
            path=".",
            search_term="",
            ast=True,
            symantic=False,
            extension=None,
            file=False,
            dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert captured_extension == "py"
    assert captured_multi is False
    assert captured_preview_size_percent == 75.0
    option_key = "demo.sample    [demo.py:3]"
    assert option_key in captured_preview_map
    assert "def sample() -> None:\n    pass" in captured_preview_map[option_key]
    printed_json = print_json.call_args.args[0]
    assert '"path": "demo.sample"' in printed_json
    assert '"body"' not in printed_json


def test_seek_ast_supports_single_python_file_path(tmp_path: Path) -> None:
    source_path = tmp_path.joinpath("demo.py")
    source_path.write_text(
        textwrap.dedent(
            """
            def sample() -> None:
                return None
            """
        ).lstrip(),
        encoding="utf-8",
    )

    def _fake_choose(*, options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> str | None:
        assert extension == "py"
        assert multi is False
        assert preview_size_percent == 75.0
        return next(iter(options_to_preview_mapping))

    with patch("machineconfig.utils.options_utils.tv_options.choose_from_dict_with_preview", side_effect=_fake_choose), patch(
        "rich.print_json"
    ) as print_json:
        seek_impl.seek(
            path=str(source_path),
            search_term="",
            ast=True,
            symantic=False,
            extension=None,
            file=False,
            dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    printed_json = print_json.call_args.args[0]
    assert '"path": "demo.sample"' in printed_json
    assert '"file_path": "demo.py"' in printed_json
