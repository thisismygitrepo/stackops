import os
import subprocess
from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_self_repo
from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.source_of_truth import STACKOPS_REPO_DIR


def readme() -> None:
    from email import message_from_string

    from rich.console import Console
    from rich.markdown import Markdown

    repo_root = cli_self_repo.developer_repo_root()
    console = Console()

    if repo_root is not None:
        readme_path = repo_root.joinpath("README.md")
        if not readme_path.is_file():
            typer.echo(f"❌ README.md not found at {str(readme_path)}")
            raise typer.Exit(code=1)
        try:
            markdown_text = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            typer.echo(f"❌ Failed to read README.md: {exc}")
            raise typer.Exit(code=1)
    else:
        from importlib.metadata import PackageNotFoundError, distribution

        try:
            metadata_text = distribution("stackops").read_text("METADATA")
        except PackageNotFoundError:
            typer.echo("❌ Installed stackops package metadata is not available.")
            raise typer.Exit(code=1)
        if metadata_text is None:
            typer.echo("❌ Installed stackops package metadata file is not available.")
            raise typer.Exit(code=1)
        markdown_text = message_from_string(metadata_text).get_payload()
        if not isinstance(markdown_text, str):
            typer.echo("❌ Installed stackops package metadata does not include a plain-text README.")
            raise typer.Exit(code=1)
        if not markdown_text:
            typer.echo("❌ Installed stackops package metadata does not include a README.")
            raise typer.Exit(code=1)

    console.print(Markdown(markdown_text))


def build_docker(
    variant: Annotated[Literal["slim", "ai"], typer.Argument(help="Variant to build: 'slim' or 'ai'")],
    docker_login_name: Annotated[
        str | None,
        typer.Option("--docker-login-name", "-n", help="Exact StackOps secrets entries[].name for Docker publish credentials."),
    ] = "docker",
    docker_account_name: Annotated[
        str | None,
        typer.Option("--docker-account-name", "-a", help="Exact StackOps secrets entries[].accountName for Docker publish credentials."),
    ] = None,
    docker_secret_name: Annotated[
        str | None,
        typer.Option("--docker-secret-name", "-N", help="Exact StackOps secrets entries[].secrets[].name for Docker publish credentials."),
    ] = None,
    docker_secret_tags: Annotated[
        list[str] | None,
        typer.Option("--docker-secret-tag", "-T", help="Exact Docker credential secret tag. Repeat for multiple tags."),
    ] = None,
    docker_scopes: Annotated[
        list[str] | None,
        typer.Option("--docker-scope", "-S", help="Exact Docker credential secret scope. Repeat for multiple scopes."),
    ] = None,
    docker_token_key: Annotated[
        str | None,
        typer.Option(
            "--docker-token-key",
            "-k",
            help="Env var key in keyValues to pass to docker login. Defaults to the first match in: DOCKER_TOKEN, DOCKERHUB_TOKEN, DOCKER_PASSWORD, DOCKER_PAT.",
        ),
    ] = None,
    docker_secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--docker-secrets-path",
            "-p",
            help="Secrets JSON path for Docker publish credentials. Read only after registry upload is confirmed.",
        ),
    ] = None,
) -> None:
    """🧱 `build_docker` — wrapper for `jobs/shell/docker_build_and_publish.sh`"""
    repo_root = cli_self_repo.developer_repo_root()
    if repo_root is None:
        typer.echo(f"❌ Developer repo not found: {STACKOPS_REPO_DIR}")
        raise typer.Exit(code=1)

    script_path = repo_root.joinpath("jobs", "shell", "docker_build_and_publish.sh")
    if not script_path.is_file():
        typer.echo(f"❌ Script not found: {str(script_path)}")
        raise typer.Exit(code=1)

    build_environment = os.environ.copy()
    build_environment.update({"STACKOPS_DOCKER_ACTION": "build", "VARIANT": variant})
    build_process = subprocess.run(["bash", str(script_path)], cwd=repo_root, env=build_environment, check=False)
    if build_process.returncode != 0:
        raise typer.Exit(code=build_process.returncode)

    if not typer.confirm("❓ Do you want to push to the registry?", default=False):
        typer.echo(f"❌ Registry upload canceled. Local image: stackops-{variant}:latest")
        return

    from stackops.secrets.search import render_secret_value
    from stackops.scripts.python.helpers.helpers_devops import cli_self_docker

    try:
        credentials = cli_self_docker.resolve_docker_credentials(
            secrets_path=docker_secrets_path,
            login_name=docker_login_name,
            account_name=docker_account_name,
            secret_name=docker_secret_name,
            secret_tags=docker_secret_tags,
            scopes=docker_scopes,
            token_key=docker_token_key,
        )
        cli_self_docker.validate_env_names(credentials.key_values)
    except cli_self_docker.DockerCredentialError as exc:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + str(exc))
        raise typer.Exit(code=1)

    typer.echo(
        typer.style("✅ Docker credentials: ", fg=typer.colors.GREEN)
        + f"using login '{credentials.login_name}' / secret '{credentials.secret_name}' "
        + f"as Docker namespace '{credentials.username}' with token env var '{credentials.token_env_key}'."
    )
    publish_environment = os.environ.copy()
    publish_environment.update({key: render_secret_value(value) for key, value in credentials.key_values.items()})
    publish_environment.update(
        {
            "STACKOPS_DOCKER_ACTION": "publish",
            "VARIANT": variant,
            "DOCKER_IMAGE_NAMESPACE": credentials.username,
            "DOCKER_LOGIN_TOKEN_ENV_VAR": credentials.token_env_key,
        }
    )
    publish_process = subprocess.run(["bash", str(script_path)], cwd=repo_root, env=publish_environment, check=False)
    if publish_process.returncode != 0:
        raise typer.Exit(code=publish_process.returncode)


def build_graph(
    view: Annotated[
        bool,
        typer.Option("--view", "-v", help="Preview the generated HTML graph in the browser."),
    ] = False,
) -> None:
    """🕸 <g> Build the architecture dependency graph."""
    repo_root = cli_self_repo.developer_repo_root()
    if repo_root is None:
        typer.echo(f"❌ Developer repo not found: {STACKOPS_REPO_DIR}")
        raise typer.Exit(code=1)

    from stackops.architecture_graph.cli import DEFAULT_OUTPUT_PATH, DEFAULT_PACKAGE_NAME, DEFAULT_SOURCE_ROOT
    from stackops.architecture_graph.graph import build_graph_page_payload
    from stackops.architecture_graph.renderer import write_html

    source_root = repo_root.joinpath(DEFAULT_SOURCE_ROOT)
    output_path = repo_root.joinpath(DEFAULT_OUTPUT_PATH)
    payload = build_graph_page_payload(
        source_root=source_root,
        package_name=DEFAULT_PACKAGE_NAME,
        initial_depth=1,
        max_depth=3,
    )
    written = write_html(payload=payload, output_path=output_path)
    typer.echo(f"Wrote {written}")

    if view:
        from stackops.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(f'preview --backend browser "{written}"', strict=True)


def explore_cli(ctx: typer.Context) -> None:
    """🧭 <x> Explore the StackOps CLI graph."""
    from stackops.scripts.python.graph.visualize import cli_graph_app

    apply_alias_markers(cli_graph_app.get_app())(ctx.args, standalone_mode=False)


def explore_python_api(ctx: typer.Context) -> None:
    """🧭 <p> Explore the StackOps Python API graph."""
    from stackops.scripts.python.graph.visualize import python_api_graph_app

    apply_alias_markers(python_api_graph_app.get_app())(ctx.args, standalone_mode=False)


def security(ctx: typer.Context) -> None:
    """🔐 <y> Security related CLI tools."""
    import stackops.jobs.installer.checks.security_cli as security_cli_module

    apply_alias_markers(security_cli_module.get_app())(ctx.args, standalone_mode=False)


def docs(
    rebuild: Annotated[bool, typer.Option("--rebuild", "-b", help="Rebuild docs before starting the preview server.")] = False,
    create_artifacts: Annotated[
        bool, typer.Option("--create-artifacts", "-a", help="Regenerate CLI graph docs artifacts before starting the preview server.")
    ] = False,
) -> None:
    """📚 <o> Serve local docs with preview URLs."""
    from stackops.scripts.python.helpers.helpers_devops import cli_self_docs

    cli_self_docs.serve_docs(rebuild=rebuild, create_artifacts=create_artifacts)
