from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.source_of_truth import STACKOPS_REPO_DIR


def developer_repo_root() -> Path | None:
    if STACKOPS_REPO_DIR.joinpath("pyproject.toml").is_file():
        return STACKOPS_REPO_DIR
    return None


def copy_assets_all() -> None:
    from stackops.profile import create_helper

    create_helper.copy_assets_to_machine(which="scripts")
    create_helper.copy_assets_to_machine(which="settings")


def link_public_configs() -> None:
    from stackops.profile import create_links_export

    create_links_export.main_from_parser(
        direction="down", sensitivity="public", method="copy", on_conflict="overwrite-default-path", which="all"
    )


def configure_default_shell() -> None:
    from stackops.profile.create_shell_profile import create_default_shell_profile

    create_default_shell_profile()


def update(
    copy_assets: Annotated[
        bool,
        typer.Option(
            "--copy-assets", "-a", help="Copy assets to machine after update (scripts + settings, overwrites local assets)."
        ),
    ] = False,
    sync_public: Annotated[
        bool,
        typer.Option(
            "--link-public-configs",
            "-l",
            help="Sync public configs down after update (overwrites your configs at their default paths).",
        ),
    ] = False,
    config_shell: Annotated[
        bool,
        typer.Option(
            "--config-shell", "-s", help="Create or configure the default shell profile after update."
        ),
    ] = False,
) -> None:
    """🔄 UPDATE uv and stackops

    Each flag independently triggers one post-update action:
    --copy-assets        -> devops config copy-assets all
    --link-public-configs -> devops config sync down --sensitivity public --method copy --on-conflict overwrite-default-path --which all
    --config-shell       -> devops config terminal config-shell --which default
    """
    dev_repo_root = developer_repo_root()
    if dev_repo_root is not None:
        shell_script = f"""
uv self update
cd "{STACKOPS_REPO_DIR}"
git pull --ff-only
uv tool install --no-cache --upgrade --editable "{STACKOPS_REPO_DIR}"
"""
    else:
        shell_script = """
uv self update
uv tool install --no-cache --upgrade stackops
"""
    import platform

    if platform.system() == "Windows":
        from stackops.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function

        any_post = copy_assets or sync_public or config_shell
        full_script = shell_script
        if any_post:
            def _post_update() -> None:
                if copy_assets:
                    copy_assets_all()
                if sync_public:
                    link_public_configs()
                if config_shell:
                    configure_default_shell()

            uv_command, _py_file = get_shell_script_running_lambda_function(
                lmb=_post_update, uv_with=["stackops"], uv_project_dir=None
            )
            full_script = shell_script + "\n" + uv_command
        exit_then_run_shell_script(full_script, strict=True)
    else:
        from stackops.utils.code import run_shell_script

        proc = run_shell_script(shell_script, display_script=True, clean_env=False)
        if proc.returncode != 0:
            typer.echo(f"❌ Update script failed with return code {proc.returncode}")
            raise typer.Exit(code=proc.returncode)
        if copy_assets:
            copy_assets_all()
        if sync_public:
            link_public_configs()
        if config_shell:
            configure_default_shell()


def _install_stackops(dev: bool) -> None:
    from stackops.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function, get_uv_command
    from stackops.utils.ssh_utils.abc import STACKOPS_REQUIREMENT
    import platform

    stackops_path = STACKOPS_REPO_DIR
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
{uv_command} sync --no-dev
{uv_command} tool install --upgrade --editable "{str(stackops_path)}"
{uv_command2}
""", strict=True)
    else:
        exit_then_run_shell_script(rf"""
{uv_command} tool install --upgrade "{STACKOPS_REQUIREMENT}"
{uv_command2}
""", strict=True)


def install(dev: Annotated[bool, typer.Option("--dev", "-d", help="Clone repo and install from it instead of PyPI")] = False) -> None:
    """📋 install stackops locally for nightly updates."""
    _install_stackops(dev=dev)


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


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops import cli_self_assets
    from stackops.scripts.python.helpers.helpers_devops.cli_self_clone import clone
    from stackops.scripts.python.helpers.helpers_devops.cli_self_export import download_installer, export
    from stackops.scripts.python.helpers.helpers_devops.cli_self_info import (
        build_docker,
        build_graph,
        docs,
        explore_cli,
        explore_python_api,
        readme,
        security,
    )

    cli_app = typer.Typer(help="🔄 <s> self operations subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }
    cli_app.command(name="install", no_args_is_help=False, help="📋 <i> install stackops locally for nightly updates.")(install)
    cli_app.command(name="i", no_args_is_help=False, help="install stackops locally for nightly updates.", hidden=True)(install)
    cli_app.command(name="clone", no_args_is_help=False, help="📥 <c> Clone the StackOps source checkout.")(clone)
    cli_app.command(name="c", no_args_is_help=False, help="Clone the StackOps source checkout.", hidden=True)(clone)
    cli_app.command(name="update", no_args_is_help=False, help="🔄 <u> UPDATE stackops")(update)
    cli_app.command(name="u", no_args_is_help=False, hidden=True)(update)
    cli_app.command(name="status", no_args_is_help=False, help="📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.")(status)
    cli_app.command(name="s", no_args_is_help=False, help="STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.", hidden=True)(status)

    cli_app.command(name="security", help="🔐 <y> Security related CLI tools.", context_settings=ctx_settings)(security)
    cli_app.command(name="y", help="🔐 <y> Security related CLI tools.", hidden=True, context_settings=ctx_settings)(security)

    cli_app.command(name="explore-cli", help="🧭 <x> Explore the StackOps CLI graph.", context_settings=ctx_settings)(explore_cli)
    cli_app.command(name="explore", help="Explore the StackOps CLI graph.", hidden=True, context_settings=ctx_settings)(explore_cli)
    cli_app.command(name="x", hidden=True, context_settings=ctx_settings)(explore_cli)
    cli_app.command(name="explore-python-api", help="🧭 <p> Explore the StackOps Python API graph.", context_settings=ctx_settings)(
        explore_python_api
    )
    cli_app.command(name="explore-api", help="Explore the StackOps Python API graph.", hidden=True, context_settings=ctx_settings)(
        explore_python_api
    )
    cli_app.command(name="p", hidden=True, context_settings=ctx_settings)(explore_python_api)

    cli_app.command(name="readme", no_args_is_help=False, help="📚 <r> render readme markdown in terminal.")(readme)
    cli_app.command(name="r", no_args_is_help=False, hidden=True)(readme)

    dev_repo_root = developer_repo_root()
    if dev_repo_root is not None:
        cli_app.command(name="docs", no_args_is_help=False, help="📚 <o> Serve local docs with preview URLs.")(docs)
        cli_app.command(name="o", no_args_is_help=False, hidden=True)(docs)

    cli_app.command(name="build-installer", no_args_is_help=False, help="📤 <e> Build an offline installer.")(export)
    cli_app.command(name="e", no_args_is_help=False, help="Export the installation files to get an offline image.", hidden=True)(export)
    cli_app.command(name="download-installer", no_args_is_help=False, help="📥 <D> Download an offline installer.")(download_installer)
    cli_app.command(name="D", no_args_is_help=False, help="Download and extract a published offline installer.", hidden=True)(
        download_installer
    )

    if dev_repo_root is not None:
        cli_app.command(name="build-docker", no_args_is_help=False, help="🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)")(
            build_docker
        )
        cli_app.command(name="d", no_args_is_help=False, help="Build docker images (wraps jobs/shell/docker_build_and_publish.sh)", hidden=True)(
            build_docker
        )
        cli_app.command(name="build-graph", no_args_is_help=False, help="🕸 <g> Build the architecture dependency graph.")(build_graph)
        cli_app.command(name="g", no_args_is_help=False, help="Build the architecture dependency graph.", hidden=True)(build_graph)
        cli_app.add_typer(cli_self_assets.get_app(), name="build-assets", help="🗂 <a> Regenerate repo-local CLI and skill assets.")
        cli_app.add_typer(cli_self_assets.get_app(), name="a", help="Regenerate repo-local CLI and skill assets.", hidden=True)

    return cli_app
