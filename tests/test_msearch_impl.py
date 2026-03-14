from unittest.mock import patch

from machineconfig.scripts.python.helpers.helpers_msearch import msearch_impl


def test_machineconfig_search_keeps_default_file_source_when_dotfiles_allowed() -> None:
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
            no_dotfiles=False,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert run_shell_script.call_count == 1
    script = run_shell_script.call_args.kwargs["script"]
    assert not script.startswith("fd ")


def test_machineconfig_search_limits_fd_source_to_files_when_excluding_dotfiles() -> None:
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
            no_dotfiles=True,
            rga=False,
            edit=False,
            install_dependencies=False,
        )

    assert run_shell_script.call_count == 1
    script = run_shell_script.call_args.kwargs["script"]
    assert script.startswith("fd --type file | ")
