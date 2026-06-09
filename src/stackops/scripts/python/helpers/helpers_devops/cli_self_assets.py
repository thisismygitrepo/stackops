import typer


def update_cli_graph() -> None:
    """🧩 <g> Regenerate the checked-in CLI graph snapshot."""
    from stackops.scripts.python.helpers.helpers_devops import cli_self_docs

    repo_root = cli_self_docs.get_docs_repo_root()
    cli_self_docs.write_cli_graph_snapshot(repo_root=repo_root)


def update_stackops_skill_refs() -> None:
    """📚 <s> Regenerate the StackOps skill CLI reference maps."""
    from stackops.scripts.python.helpers.helpers_devops import cli_self_docs, stackops_skill_refs

    repo_root = cli_self_docs.get_docs_repo_root()
    cli_self_docs.write_cli_graph_snapshot(repo_root=repo_root)
    generated_paths = stackops_skill_refs.write_stackops_skill_references(repo_root=repo_root)
    for generated_path in generated_paths:
        typer.echo(f"""Regenerated StackOps skill reference: {generated_path.relative_to(repo_root).as_posix()}""")


def regenerate_charts() -> None:
    """☀ <c> Regenerate the checked-in sunburst HTML chart."""
    from stackops.scripts.python.helpers.helpers_devops import cli_self_docs

    repo_root = cli_self_docs.get_docs_repo_root()
    artifact_spec = next((spec for spec in cli_self_docs.DOCS_ARTIFACT_SPECS if spec.view == "sunburst"), None)
    if artifact_spec is None:
        typer.echo("""❌ ERROR: Missing docs artifact spec for "sunburst".""", err=True)
        raise typer.Exit(code=1)
    cli_self_docs.render_docs_artifact(
        repo_root=repo_root,
        artifact_spec=artifact_spec,
    )


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🗂 <a> Regenerate repo-local CLI and skill assets.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    cli_app.command(
        name="update-cli-graph",
        no_args_is_help=False,
        help="🧩 <g> Regenerate the checked-in CLI graph snapshot.",
    )(update_cli_graph)
    cli_app.command(
        name="g",
        no_args_is_help=False,
        help="Regenerate the checked-in CLI graph snapshot.",
        hidden=True,
    )(update_cli_graph)
    cli_app.command(
        name="regenerate-charts",
        no_args_is_help=False,
        help="☀ <c> Regenerate the checked-in sunburst HTML chart.",
    )(regenerate_charts)
    cli_app.command(
        name="c",
        no_args_is_help=False,
        help="Regenerate the checked-in sunburst HTML chart.",
        hidden=True,
    )(regenerate_charts)
    cli_app.command(
        name="update-skill-refs",
        no_args_is_help=False,
        help="📚 <s> Regenerate the StackOps skill CLI reference maps.",
    )(update_stackops_skill_refs)
    cli_app.command(
        name="s",
        no_args_is_help=False,
        help="Regenerate the StackOps skill CLI reference maps.",
        hidden=True,
    )(update_stackops_skill_refs)
    return cli_app
