import typer
from pathlib import Path
from typing import Annotated, Literal

from machineconfig.utils.ssh_utils.abc import MACHINECONFIG_VERSION


def _developer_repo_root() -> Path | None:
    repo_root = Path.home().joinpath("code", "machineconfig")
    if repo_root.joinpath("pyproject.toml").is_file():
        return repo_root
    return None


def copy_both_assets() -> None:
    from machineconfig.profile import create_helper

    create_helper.copy_assets_to_machine(which="scripts")
    create_helper.copy_assets_to_machine(which="settings")


def init(
    which: Annotated[
        Literal["init", "ia", "live"], typer.Argument(..., help="Comma-separated list of script names to run all initialization scripts.")
    ] = "init",
    run: Annotated[bool, typer.Option("--run/--no-run", "-r/-nr", help="Run the script after displaying it.")] = False,
) -> None:
    import platform

    script = ""
    if platform.system() == "Linux" or platform.system() == "Darwin":
        match which:
            case "init":
                import machineconfig.settings as module

                if platform.system() == "Darwin":
                    init_path = Path(module.__file__).parent.joinpath("shells", "zsh", "init.sh")
                else:
                    init_path = Path(module.__file__).parent.joinpath("shells", "bash", "init.sh")
                script = init_path.read_text(encoding="utf-8")
            case "ia":
                import machineconfig.setup_linux.web_shortcuts as module
                from machineconfig.setup_linux.web_shortcuts import INTERACTIVE_PATH_REFERENCE

                script_path = Path(module.__file__).parent.joinpath(INTERACTIVE_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case "live":
                import machineconfig.setup_linux.web_shortcuts as module
                from machineconfig.setup_linux.web_shortcuts import LIVE_FROM_GITHUB_PATH_REFERENCE

                script_path = Path(module.__file__).parent.joinpath(LIVE_FROM_GITHUB_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case _:
                typer.echo("Unsupported shell script for Linux.")
                raise typer.Exit(code=1)

    elif platform.system() == "Windows":
        match which:
            case "init":
                import machineconfig.settings as module

                init_path = Path(module.__file__).parent.joinpath("shells", "pwsh", "init.ps1")
                script = init_path.read_text(encoding="utf-8")
            case "ia":
                import machineconfig.setup_windows.web_shortcuts as module
                from machineconfig.setup_windows.web_shortcuts import INTERACTIVE_PATH_REFERENCE

                script_path = Path(module.__file__).parent.joinpath(INTERACTIVE_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case "live":
                import machineconfig.setup_windows.web_shortcuts as module
                from machineconfig.setup_windows.web_shortcuts import LIVE_FROM_GITHUB_PATH_REFERENCE

                script_path = Path(module.__file__).parent.joinpath(LIVE_FROM_GITHUB_PATH_REFERENCE)
                script = script_path.read_text(encoding="utf-8")
            case _:
                typer.echo("Unsupported shell script for Windows.")
                raise typer.Exit(code=1)
                # return
    else:
        # raise NotImplementedError("Unsupported platform")
        typer.echo("Unsupported platform for init scripts.")
        raise typer.Exit(code=1)
    if run:
        from machineconfig.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script, strict=True)
    else:
        print(script)


def update(
    link_public_configs: Annotated[
        bool,
        typer.Option("--link-public-configs/--no-link-public-configs", "-b/-nb", help="Link public configs after update (overwrites your configs!)"),
    ] = False,
):
    """🔄 UPDATE uv and machineconfig"""
    if Path.home().joinpath("code", "machineconfig").exists():
        shell_script = """
uv self update
cd ~/code/machineconfig
git pull
uv tool install --no-cache --upgrade --editable $HOME/code/machineconfig
    """
    else:
        shell_script = """
uv self update
uv tool install --no-cache --upgrade machineconfig
    """
    import platform

    if platform.system() == "Windows":
        from machineconfig.utils.code import exit_then_run_shell_script, get_uv_command_executing_python_script
        from machineconfig.utils.meta import lambda_to_python_script

        python_script = lambda_to_python_script(
            lambda: copy_both_assets(),  # pylint: disable=unnecessary-lambda
            in_global=True,
            import_module=False,
        )
        uv_command, _py_file = get_uv_command_executing_python_script(python_script=python_script, uv_with=["machineconfig"], uv_project_dir=None)
        exit_then_run_shell_script(shell_script + "\n" + uv_command, strict=True)
    else:
        from machineconfig.utils.code import run_shell_script

        run_shell_script(shell_script, display_script=True, clean_env=False)
        copy_both_assets()
        if link_public_configs:
            from machineconfig.profile import create_links_export

            create_links_export.main_from_parser(
                direction="down", sensitivity="public", method="copy", on_conflict="overwrite-default-path", which="all"
            )


def _install_machineconfig(dev: bool) -> None:
    from machineconfig.utils.code import exit_then_run_shell_script, get_shell_script_running_lambda_function, get_uv_command
    import platform

    mcfg_path = Path.home().joinpath("code/machineconfig")
    if dev and not mcfg_path.exists():
        import git

        mcfg_path.parent.mkdir(parents=True, exist_ok=True)
        git.Repo.clone_from("https://github.com/thisismygitrepo/machineconfig.git", str(mcfg_path))

    uv_command = get_uv_command(platform=platform.system())

    def func() -> None:
        from machineconfig.profile.create_shell_profile import create_default_shell_profile

        create_default_shell_profile()

    uv_command2, _script_path = get_shell_script_running_lambda_function(
        lambda: func(),  # pylint: disable=unnecessary-lambda
        uv_with=["machineconfig"],
        uv_project_dir=None,
    )
    if mcfg_path.exists():
        exit_then_run_shell_script(f"""
cd {str(mcfg_path)}
{uv_command} sync
{uv_command} tool install --upgrade --editable "{str(mcfg_path)}"
{uv_command2}
""")
    else:
        exit_then_run_shell_script(rf"""
{uv_command} tool install --upgrade "{MACHINECONFIG_VERSION}"
{uv_command2}
""")


def install(dev: Annotated[bool, typer.Option("--dev", "-d", help="Clone repo and install from it instead of PyPI")] = False):
    """📋 install machineconfig locally for nightly updates."""
    _install_machineconfig(dev=dev)


def export() -> None:
    """📤 export the installation files to get an offline image."""
    from machineconfig.utils.installer_utils import installer_offline

    installer_offline.export()


def interactive() -> None:
    """🤖 <c> INTERACTIVE configuration of machine."""
    from machineconfig.scripts.python.helpers.helpers_devops.interactive import main

    main()


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
    import machineconfig.scripts.python.helpers.helpers_devops.devops_status as helper

    sections = helper.resolve_sections(machine=machine, shell=shell, repos=repos, ssh=ssh, configs=configs, apps=apps, backup=backup)
    helper.main(sections=sections)


def readme() -> None:
    from rich.console import Console
    from rich.markdown import Markdown
    import requests

    # URL of the raw README.md file
    url_readme = "https://raw.githubusercontent.com/thisismygitrepo/machineconfig/refs/heads/main/README.md"

    # Fetch the content
    response = requests.get(url_readme, timeout=10)
    response.raise_for_status()  # Raise an error for bad responses

    # Parse markdown
    md = Markdown(response.text)

    # Render in terminal
    console = Console()
    console.print(md)


def buid_docker(variant: Annotated[Literal["slim", "ai"], typer.Argument(..., help="Variant to build: 'slim' or 'ai'")] = "slim") -> None:
    """🧱 `buid_docker` — wrapper for `jobs/shell/docker_build_and_publish.sh`"""
    import machineconfig

    script_path = Path(machineconfig.__file__).resolve().parent.parent.parent.joinpath("jobs", "shell", "docker_build_and_publish.sh")
    if not script_path.exists():
        typer.echo(f"❌ Script not found: {str(script_path)}")
        raise typer.Exit(code=1)

    # shell_cmd = f'VARIANT="{variant}" && bash "{str(script_path)}"'\
    from machineconfig.utils.source_of_truth import REPO_ROOT

    shell_cmd = f"""
export VARIANT="{variant}"
cd "{str(REPO_ROOT)}"
bash "{str(script_path)}"
"""
    # Use exit_then_run_shell_script for interactive runs (keeps tty), otherwise run shell script non-interactively
    from machineconfig.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(shell_cmd, strict=True)


def explore(ctx: typer.Context) -> None:
    """🧭 <x> Explore the MachineConfig CLI graph."""
    from machineconfig.scripts.python.graph.visualize import cli_graph_app

    cli_graph_app.get_app()(ctx.args, standalone_mode=False)


def security(ctx: typer.Context) -> None:
    """🔐 <y> Security related CLI tools."""
    import machineconfig.jobs.installer.checks.security_cli as security_cli_module

    security_cli_module.get_app()(ctx.args, standalone_mode=False)


def docs(
    rebuild: Annotated[bool, typer.Option("--rebuild", "-b", help="Rebuild docs before starting the preview server.")] = False,
    create_artifacts: Annotated[
        bool, typer.Option("--create-artifacts", "-a", help="Regenerate CLI graph docs artifacts before starting the preview server.")
    ] = False,
) -> None:
    """📚 <o> Serve local docs with preview URLs."""
    from machineconfig.scripts.python.helpers.helpers_devops import cli_self_docs

    cli_self_docs.serve_docs(rebuild=rebuild, create_artifacts=create_artifacts)


def get_app() -> typer.Typer:
    from machineconfig.scripts.python.helpers.helpers_devops import cli_self_assets
    from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai import app as cli_self_ai_app

    cli_app = typer.Typer(help="🔄 <s> self operations subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }
    cli_app.command(name="install", no_args_is_help=False, help="📋 <i> install machineconfig locally for nightly updates.")(install)
    cli_app.command(name="i", no_args_is_help=False, help="install machineconfig locally for nightly updates.", hidden=True)(install)
    cli_app.command(name="update", no_args_is_help=False, help="🔄 <u> UPDATE machineconfig")(update)
    cli_app.command(name="u", no_args_is_help=False, hidden=True)(update)
    cli_app.command(name="status", no_args_is_help=False, help="📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.")(status)
    cli_app.command(name="s", no_args_is_help=False, help="STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.", hidden=True)(status)
    cli_app.command(name="config", no_args_is_help=False, help="🤖 <c> interactive configuration of machine.")(interactive)
    cli_app.command(name="c", no_args_is_help=False, help="INTERACTIVE configuration of machine.", hidden=True)(interactive)

    cli_app.command(name="security", help="🔐 <y> Security related CLI tools.", context_settings=ctx_settings)(security)
    cli_app.command(name="y", help="🔐 <y> Security related CLI tools.", hidden=True, context_settings=ctx_settings)(security)

    cli_app.command(name="init", no_args_is_help=False, help="🦐 <t> Define and manage configurations")(init)
    cli_app.command(name="t", no_args_is_help=False, hidden=True)(init)

    cli_app.command(name="explore", help="🧭 <x> Explore the MachineConfig CLI graph.", context_settings=ctx_settings)(explore)
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
            buid_docker
        )
        cli_app.command(name="d", no_args_is_help=False, help="Build docker images (wraps jobs/shell/docker_build_and_publish.sh)", hidden=True)(
            buid_docker
        )
        cli_app.add_typer(cli_self_assets.get_app(), name="build-assets", help="🗂 <a> Regenerate repo-local CLI graph assets.")
        cli_app.add_typer(cli_self_assets.get_app(), name="ba", help="Regenerate repo-local CLI graph assets.", hidden=True)
        cli_app.add_typer(cli_self_ai_app.get_app(), name="workflows", help="🤖 <w> Developer AI workflows.")
        cli_app.add_typer(cli_self_ai_app.get_app(), name="w", help="Developer AI workflows.", hidden=True)

    return cli_app
