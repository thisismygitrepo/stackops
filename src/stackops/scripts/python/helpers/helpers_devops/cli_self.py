from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.utils.ssh_utils.abc import STACKOPS_VERSION


def _developer_repo_root() -> Path | None:
    repo_root = Path.home().joinpath("code", "stackops")
    if repo_root.joinpath("pyproject.toml").is_file():
        return repo_root
    return None


def copy_both_assets() -> None:
    from stackops.profile import create_helper

    create_helper.copy_assets_to_machine(which="scripts")
    create_helper.copy_assets_to_machine(which="settings")


def copy_assets_and_link_public_configs() -> None:
    copy_both_assets()
    from stackops.profile import create_links_export

    create_links_export.main_from_parser(
        direction="down", sensitivity="public", method="copy", on_conflict="overwrite-default-path", which="all"
    )


def update(
    link_public_configs: Annotated[
        bool,
        typer.Option("--link-public-configs/--no-link-public-configs", "-b/-nb", help="Link public configs after update (overwrites your configs!)"),
    ] = False,
) -> None:
    """🔄 UPDATE uv and stackops"""
    developer_repo_root = _developer_repo_root()
    if developer_repo_root is not None:
        shell_script = """
uv self update
cd "$HOME/code/stackops"
git pull --ff-only
uv tool install --no-cache --upgrade --editable "$HOME/code/stackops"
    """
    else:
        shell_script = """
uv self update
uv tool install --no-cache --upgrade stackops
    """
    import platform

    if platform.system() == "Windows":
        from stackops.utils.code import exit_then_run_shell_script, get_uv_command_executing_python_script
        from stackops.utils.meta import lambda_to_python_script

        if link_public_configs:
            python_script = lambda_to_python_script(
                lambda: copy_assets_and_link_public_configs(),  # pylint: disable=unnecessary-lambda
                in_global=True,
                import_module=False,
            )
        else:
            python_script = lambda_to_python_script(
                lambda: copy_both_assets(),  # pylint: disable=unnecessary-lambda
                in_global=True,
                import_module=False,
            )
        uv_command, _py_file = get_uv_command_executing_python_script(python_script=python_script, uv_with=["stackops"], uv_project_dir=None)
        exit_then_run_shell_script(shell_script + "\n" + uv_command, strict=True)
    else:
        from stackops.utils.code import run_shell_script

        run_shell_script(shell_script, display_script=True, clean_env=False)
        if link_public_configs:
            copy_assets_and_link_public_configs()
        else:
            copy_both_assets()


def _install_stackops(dev: bool) -> None:
    from stackops.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function, get_uv_command
    import platform

    stackops_path = Path.home().joinpath("code", "stackops")
    if dev and not stackops_path.exists():
        import git

        stackops_path.parent.mkdir(parents=True, exist_ok=True)
        git.Repo.clone_from("https://github.com/thisismygitrepo/stackops.git", str(stackops_path))

    uv_command = get_uv_command(platform=platform.system())

    def func() -> None:
        from stackops.profile.create_shell_profile import create_default_shell_profile

        create_default_shell_profile()

    uv_command2, _script_path = get_shell_script_running_lambda_function(
        lambda: func(),  # pylint: disable=unnecessary-lambda
        uv_with=["stackops"],
        uv_project_dir=None,
    )
    if dev:
        if not stackops_path.joinpath("pyproject.toml").is_file():
            typer.echo(f"Cannot install editable stackops from {str(stackops_path)} because pyproject.toml is missing.")
            raise typer.Exit(code=1)

        exit_then_run_shell_script(f"""
cd "{str(stackops_path)}"
{uv_command} sync
{uv_command} tool install --upgrade --editable "{str(stackops_path)}"
{uv_command2}
""", strict=True)
    else:
        exit_then_run_shell_script(rf"""
{uv_command} tool install --upgrade "{STACKOPS_VERSION}"
{uv_command2}
""", strict=True)


def install(dev: Annotated[bool, typer.Option("--dev", "-d", help="Clone repo and install from it instead of PyPI")] = False) -> None:
    """📋 install stackops locally for nightly updates."""
    _install_stackops(dev=dev)


def export() -> None:
    """📤 export the installation files to get an offline image."""
    from stackops.utils.installer_utils import installer_offline

    installer_offline.export()


def status(
    machine: Annotated[bool, typer.Option("--machine", "-m", help="Show the machine/system information section.")] = False,
    shell: Annotated[bool, typer.Option("--shell", "-s", help="Show the shell profile section.")] = False,
    repos: Annotated[bool, typer.Option("--repos", "-r", help="Show the configured repositories section.")] = False,
    ssh: Annotated[bool, typer.Option("--ssh", "-h", help="Show the SSH configuration section.")] = False,
    configs: Annotated[
        bool, typer.Option("--configs", "--dotfiles", "--symlinks", "-c", "-d", "-l", help="Show the linked config, dotfile, and symlink section.")
    ] = False,
    apps: Annotated[bool, typer.Option("--apps", "--tools", "-a", "-t", help="Show the installed apps/tools section.")] = False,
    backup: Annotated[bool, typer.Option("--backup", "-b", help="Show the backup configuration section.")] = False,
) -> None:
    """📊 STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.

    Pass one or more section flags to limit the report to those sections.
    """
    import stackops.scripts.python.helpers.helpers_devops.devops_status as helper

    sections = helper.resolve_sections(machine=machine, shell=shell, repos=repos, ssh=ssh, configs=configs, apps=apps, backup=backup)
    helper.main(sections=sections)


def readme() -> None:
    from rich.console import Console
    from rich.markdown import Markdown

    repo_root = _developer_repo_root()
    if repo_root is not None:
        markdown_text = repo_root.joinpath("README.md").read_text(encoding="utf-8")
    else:
        import requests

        url_readme = "https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/README.md"
        response = requests.get(url_readme, timeout=10)
        response.raise_for_status()
        markdown_text = response.text

    console = Console()
    console.print(Markdown(markdown_text))


def build_docker(variant: Annotated[Literal["slim", "ai"], typer.Argument(help="Variant to build: 'slim' or 'ai'")] = "slim") -> None:
    """🧱 `build_docker` — wrapper for `jobs/shell/docker_build_and_publish.sh`"""
    repo_root = _developer_repo_root()
    if repo_root is None:
        typer.echo("❌ Developer repo not found: ~/code/stackops")
        raise typer.Exit(code=1)

    script_path = repo_root.joinpath("jobs", "shell", "docker_build_and_publish.sh")
    if not script_path.is_file():
        typer.echo(f"❌ Script not found: {str(script_path)}")
        raise typer.Exit(code=1)

    shell_cmd = f"""
export VARIANT="{variant}"
cd "{str(repo_root)}"
bash "{str(script_path)}"
"""
    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(shell_cmd, strict=True)


def explore(ctx: typer.Context) -> None:
    """🧭 <x> Explore the StackOps CLI graph."""
    from stackops.scripts.python.graph.visualize import cli_graph_app

    cli_graph_app.get_app()(ctx.args, standalone_mode=False)


def security(ctx: typer.Context) -> None:
    """🔐 <y> Security related CLI tools."""
    import stackops.jobs.installer.checks.security_cli as security_cli_module

    security_cli_module.get_app()(ctx.args, standalone_mode=False)


def docs(
    rebuild: Annotated[bool, typer.Option("--rebuild", "-b", help="Rebuild docs before starting the preview server.")] = False,
    create_artifacts: Annotated[
        bool, typer.Option("--create-artifacts", "-a", help="Regenerate CLI graph docs artifacts before starting the preview server.")
    ] = False,
) -> None:
    """📚 <o> Serve local docs with preview URLs."""
    from stackops.scripts.python.helpers.helpers_devops import cli_self_docs

    cli_self_docs.serve_docs(rebuild=rebuild, create_artifacts=create_artifacts)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops import cli_self_assets
    from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import app as cli_self_ai_app

    cli_app = typer.Typer(help="🔄 <s> self operations subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }
    cli_app.command(name="install", no_args_is_help=False, help="📋 <i> install stackops locally for nightly updates.")(install)
    cli_app.command(name="i", no_args_is_help=False, help="install stackops locally for nightly updates.", hidden=True)(install)
    cli_app.command(name="update", no_args_is_help=False, help="🔄 <u> UPDATE stackops")(update)
    cli_app.command(name="u", no_args_is_help=False, hidden=True)(update)
    cli_app.command(name="status", no_args_is_help=False, help="📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.")(status)
    cli_app.command(name="s", no_args_is_help=False, help="STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.", hidden=True)(status)

    cli_app.command(name="security", help="🔐 <y> Security related CLI tools.", context_settings=ctx_settings)(security)
    cli_app.command(name="y", help="🔐 <y> Security related CLI tools.", hidden=True, context_settings=ctx_settings)(security)

    cli_app.command(name="explore", help="🧭 <x> Explore the StackOps CLI graph.", context_settings=ctx_settings)(explore)
    cli_app.command(name="x", hidden=True, context_settings=ctx_settings)(explore)

    cli_app.command(name="readme", no_args_is_help=False, help="📚 <r> render readme markdown in terminal.")(readme)
    cli_app.command(name="r", no_args_is_help=False, hidden=True)(readme)

    developer_repo_root = _developer_repo_root()
    if developer_repo_root is not None:
        cli_app.command(name="docs", no_args_is_help=False, help="📚 <o> Serve local docs with preview URLs.")(docs)
        cli_app.command(name="o", no_args_is_help=False, hidden=True)(docs)

    cli_app.command(name="build-installer", no_args_is_help=False, help="📤 <e> Build an offline installer.")(export)
    cli_app.command(name="e", no_args_is_help=False, help="Export the installation files to get an offline image.", hidden=True)(export)

    if developer_repo_root is not None:
        cli_app.command(name="build-docker", no_args_is_help=False, help="🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)")(
            build_docker
        )
        cli_app.command(name="d", no_args_is_help=False, help="Build docker images (wraps jobs/shell/docker_build_and_publish.sh)", hidden=True)(
            build_docker
        )
        cli_app.add_typer(cli_self_assets.get_app(), name="build-assets", help="🗂 <a> Regenerate repo-local CLI graph assets.")
        cli_app.add_typer(cli_self_assets.get_app(), name="ba", help="Regenerate repo-local CLI graph assets.", hidden=True)
        cli_app.add_typer(cli_self_ai_app.get_app(), name="workflows", help="🤖 <w> Developer AI workflows.")
        cli_app.add_typer(cli_self_ai_app.get_app(), name="w", help="Developer AI workflows.", hidden=True)

    return cli_app
