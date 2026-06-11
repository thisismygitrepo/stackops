"""devops with emojis - lazy loading subcommands."""

from typing import Annotated, Callable, TypedDict

import typer

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


class EmojiDisplayDiagnostic(TypedDict):
    emoji: str
    codepoints: list[str]
    char_count: int
    has_variation_selector_16: bool
    terminal_width: int | None


def emoji_display_diagnostics(emojis: list[str]) -> list[EmojiDisplayDiagnostic]:
    import unicodedata

    wcswidth_func: Callable[[str], int] | None

    try:
        from wcwidth import wcswidth

        wcswidth_func = wcswidth
    except Exception:
        wcswidth_func = None

    diagnostics: list[EmojiDisplayDiagnostic] = []
    for emoji in emojis:
        codepoints = [f"U+{ord(ch):04X} {unicodedata.name(ch, '?')}" for ch in emoji]
        diagnostics.append(
            {
                "emoji": emoji,
                "codepoints": codepoints,
                "char_count": len(emoji),
                "has_variation_selector_16": "\ufe0f" in emoji,
                "terminal_width": wcswidth_func(emoji) if wcswidth_func is not None else None,
            }
        )
    return diagnostics


def inspect_devops_help_emojis() -> list[EmojiDisplayDiagnostic]:
    return emoji_display_diagnostics(emojis=["🔧", "📁", "🔩", "💾", "🔧", "🌐", "🚀"])


def _run_nested_app(ctx: typer.Context, app_factory: Callable[[], typer.Typer], *, prog_name: str | None = None) -> None:
    if prog_name is None:
        nested_result: object = app_factory()(ctx.args, standalone_mode=False)
    else:
        nested_result = app_factory()(ctx.args, prog_name=prog_name, standalone_mode=False)
    if isinstance(nested_result, int):
        raise typer.Exit(code=nested_result)


def install(
    ctx: typer.Context,
    which: Annotated[
        str | None,
        typer.Argument(
            ...,
            help="Comma-separated list of program names to install, group name if --group is set, or category label if --explore is set.",
        ),
    ] = None,
    group: Annotated[bool, typer.Option(..., "--group", "-g", help="Treat 'which' as a group name. A group is bundle of apps.")] = False,
    interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Interactive selection of programs to install.")] = False,
    explore: Annotated[bool, typer.Option(..., "--explore", "-x", help="Explore installer categoryLabels before installing.")] = False,
    update: Annotated[bool, typer.Option(..., "--update", "-u", help="Allow reinstalling or upgrading already installed apps when supported.")] = False,
    version: Annotated[str | None, typer.Option(..., "--version", "-v", help="Specific version or tag to install when supported.")] = None,
) -> None:
    """📦 Install packages"""
    import stackops.utils.installer_utils.installer_cli as installer_entry_point

    installer_entry_point.main_installer_cli(ctx=ctx, which=which, group=group, interactive=interactive, explore=explore, update=update, version=version)


def repos(ctx: typer.Context) -> None:
    """📁 <r> Manage development repositories"""
    from stackops.scripts.python.helpers.helpers_devops import cli_repos

    _run_nested_app(ctx, cli_repos.get_app)


def config(ctx: typer.Context) -> None:
    """⚙️ <c> Configuration management"""
    from stackops.scripts.python.helpers.helpers_devops import cli_config

    _run_nested_app(ctx, cli_config.get_app, prog_name=ctx.command_path)


def data(ctx: typer.Context) -> None:
    """💾 <d> Data management"""
    from stackops.scripts.python.helpers.helpers_devops import cli_data

    _run_nested_app(ctx, cli_data.get_app)


def self_cmd(ctx: typer.Context) -> None:
    """🔧 <s> Self management"""
    from stackops.scripts.python.helpers.helpers_devops import cli_self

    _run_nested_app(ctx, cli_self.get_app)


def network(ctx: typer.Context) -> None:
    """🌐 <n> Network management"""
    import stackops.scripts.python.helpers.helpers_devops.cli_nw as cli_network

    _run_nested_app(ctx, cli_network.get_app)


def execute(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(help="Name of script to run, e.g., 'system_compute_analyzer' for system_compute_analyzer.py, or command to execute"),
    ] = "",
    source: Annotated[
        SCRIPT_SOURCE,
        typer.Option("--source", help="Source to look for the script"),
    ] = "all",
    interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Interactive selection of scripts to run")] = False,
    command: Annotated[bool | None, typer.Option(..., "--command", "-c", help="Run as command")] = False,
    list_scripts: Annotated[bool, typer.Option(..., "--list", "-l", help="List available scripts in all locations")] = False,
) -> None:
    """🚀 Execute python/shell scripts from pre-defined directories or as command."""
    import stackops.scripts.python.helpers.helpers_devops.run_script as run_py_script_module

    forwarded_args = [str(arg) for arg in ctx.args]
    run_py_script_module.run_py_script(
        ctx=ctx,
        name=name,
        source=source,
        interactive=interactive,
        command=command,
        list_scripts=list_scripts,
        forwarded_args=forwarded_args,
    )


def vault(ctx: typer.Context) -> None:
    """🔐 <v> Search Bitwarden credentials and manage vault sessions."""
    from stackops.scripts.python.helpers.helpers_devops import cli_vault

    _run_nested_app(ctx, cli_vault.get_app, prog_name=ctx.command_path)


def get_app() -> typer.Typer:
    cli_app = typer.Typer(help="🔧 DevOps operations", no_args_is_help=True, add_help_option=True, add_completion=False)
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }

    cli_app.command("install", no_args_is_help=True, help=install.__doc__, short_help="🔧 <i> Install essential packages")(install)
    cli_app.command("i", no_args_is_help=True, help=install.__doc__, hidden=True)(install)

    cli_app.command("repos", help="📁 <r> Manage development repositories", context_settings=ctx_settings)(repos)
    cli_app.command("r", hidden=True, context_settings=ctx_settings)(repos)
    cli_app.command("config", help="🔩 <c> Configuration management", context_settings=ctx_settings)(config)
    cli_app.command("c", hidden=True, context_settings=ctx_settings)(config)
    cli_app.command("data", help="💾 <d> Data management", context_settings=ctx_settings)(data)
    cli_app.command("d", hidden=True, context_settings=ctx_settings)(data)
    cli_app.command("self", help="🔧 <s> Self management", context_settings=ctx_settings)(self_cmd)
    cli_app.command("s", hidden=True, context_settings=ctx_settings)(self_cmd)
    cli_app.command("network", help="🌐 <n> Network management", context_settings=ctx_settings)(network)
    cli_app.command("n", hidden=True, context_settings=ctx_settings)(network)

    cli_app.command(
        "execute",
        no_args_is_help=True,
        short_help="🚀 <e> Execute python/shell scripts from pre-defined directories or as command",
        context_settings=ctx_settings,
    )(execute)
    cli_app.command("e", no_args_is_help=True, hidden=True, context_settings=ctx_settings)(execute)

    cli_app.command("vault", help="🔐 <v> Search Bitwarden credentials and manage vault sessions", context_settings=ctx_settings)(vault)
    cli_app.command("v", hidden=True, context_settings=ctx_settings)(vault)

    return cli_app


def main() -> None:
    app = get_app()
    app()
