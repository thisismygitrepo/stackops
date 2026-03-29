from unittest.mock import patch

from machineconfig.scripts.python.helpers.helpers_msearch import msearch_impl


def test_machineconfig_search_limits_default_file_source_to_non_dotfiles() -> None:
    with (
        patch("platform.system", return_value="Linux"),
        patch("machineconfig.utils.code.run_shell_script") as run_shell_script,
    ):
        msearch_impl.machineconfig_search(
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


def test_machineconfig_search_keeps_default_file_source_when_dotfiles_enabled() -> None:
    with (
        patch("platform.system", return_value="Linux"),
        patch("machineconfig.utils.code.run_shell_script") as run_shell_script,
    ):
        msearch_impl.machineconfig_search(
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


def test_machineconfig_search_windows_file_search_changes_directory_with_literal_path() -> None:
    with (
        patch("platform.system", return_value="Windows"),
        patch("machineconfig.utils.code.run_shell_script") as run_shell_script,
    ):
        msearch_impl.machineconfig_search(
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


def test_machineconfig_search_windows_text_search_changes_directory_with_literal_path() -> None:
    with (
        patch("platform.system", return_value="Windows"),
        patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script,
    ):
        msearch_impl.machineconfig_search(
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


def test_machineconfig_search_macos_text_search_script_does_not_exit_parent_shell() -> None:
    with (
        patch("platform.system", return_value="Darwin"),
        patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script,
    ):
        msearch_impl.machineconfig_search(
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
        code = msearch_impl.search_file_with_context(path="/tmp/My File.txt", is_temp_file=False, edit=False)

    assert '--preview-command \'bat --color=always --style=numbers --highlight-line {split: :0} "/tmp/My File.txt"\'' in code
