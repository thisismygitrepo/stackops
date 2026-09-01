import typer

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_deps import (
    check_deps,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_maintenance import (
    cleanup,
    config_linters,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_check import (
    reference_test,
    type_check,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_commands_setup import (
    init_project,
    upgrade_packages,
)


def get_app() -> typer.Typer:
    from stackops.scripts.python import agents_test_runtime as test_runtime_module
    from stackops.scripts.python import agents_type_fix as type_fix_module

    pyproject_app = typer.Typer(help="🐍 <p> Pyproject bootstrap and typing utilities", no_args_is_help=True, add_help_option=True, add_completion=False)
    pyproject_app.command(
        name="init-project",
        no_args_is_help=False,
        help="✦ <i> Initialize a project with a uv virtual environment and install dev packages.",
    )(init_project)
    pyproject_app.command(name="i", no_args_is_help=False, hidden=True)(init_project)

    pyproject_app.command(name="config-linters", no_args_is_help=False, help="🧰 <l> Add linter config files to a git repository")(config_linters)
    pyproject_app.command(name="l", no_args_is_help=False, hidden=True)(config_linters)

    pyproject_app.command(name="upgrade-packages", no_args_is_help=False, help="↑ <a> Upgrade project dependencies.")(upgrade_packages)
    pyproject_app.command(name="a", no_args_is_help=False, hidden=True)(upgrade_packages)

    pyproject_app.command(name="check-deps", no_args_is_help=False, help="🔗 <d> Check Python import dependencies and cycles.")(check_deps)
    pyproject_app.command(name="d", no_args_is_help=False, hidden=True)(check_deps)

    pyproject_app.command(name="type-check", no_args_is_help=False, help="🧪 <c> Run the lint-and-type-check suite for a repository.")(type_check)
    pyproject_app.command(name="c", no_args_is_help=False, hidden=True)(type_check)

    pyproject_app.command(name="type-fix", no_args_is_help=True, help="🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.")(type_fix_module.launch_type_fix)
    pyproject_app.command(name="f", no_args_is_help=True, hidden=True)(type_fix_module.launch_type_fix)

    pyproject_app.command(
        name="test-runtime",
        no_args_is_help=True,
        help="🧪 <R> Create and run the runtime-test workflow for Python files under the current directory.",
    )(test_runtime_module.launch_test_runtime)
    pyproject_app.command(name="R", no_args_is_help=True, hidden=True)(test_runtime_module.launch_test_runtime)

    pyproject_app.command(name="test-reference", no_args_is_help=False, help="🔎 <r> Validate _PATH_REFERENCE targets in a repository.")(reference_test)
    pyproject_app.command(name="r", no_args_is_help=False, hidden=True)(reference_test)

    pyproject_app.command(name="cleanup", no_args_is_help=False, help="🧹 <n> Clean repository directories from cache files")(cleanup)
    pyproject_app.command(name="n", no_args_is_help=False, hidden=True)(cleanup)
    return pyproject_app
